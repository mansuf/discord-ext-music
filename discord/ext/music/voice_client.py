import asyncio
import traceback
import threading

from typing import Callable, Any, Union
from discord.voice_client import VoiceClient
from discord import opus
from .playlist import Playlist
from .track import Track
from .player import MusicPlayer
from .utils.errors import (
    MusicAlreadyPlaying,
    MusicClientException,
    MusicNotPlaying,
    NoMoreSongs,
    NotConnected
)

__all__ = (
    'MusicClient',
)

class MusicClient(VoiceClient):
    """Same like :class:`discord.VoiceClient` but with playback controls for music.
    
    Each coroutine functions are thread-safe.

    You usually don't create these, you can get it from :meth:`discord.VoiceChannel.connect`

    Warning
    --------
    It is important to add parameter `cls` with value :class:`MusicClient` to :meth:`discord.VoiceChannel.connect`,
    otherwise you wont get these features. For example:

    .. code-block:: python3
        
        # Use this method
        music_client = await voice_channel.connect(cls=MusicClient)

        # But not this method
        music_client = await voice_channel.connect()
        
    """
    def __init__(self, client, channel):
        super().__init__(client, channel)
        self._after = None

        # Will be used for _stop()
        self._done = asyncio.Event()
        
        # This will be used if bot is leaving voice channel
        self._leaving = threading.Event()

        # Playlist to store tracks
        self._playlist = Playlist()

        # Will be used for music controls
        self._lock = asyncio.Lock()

    async def on_voice_state_update(self, data):
        self.session_id = data['session_id']
        channel_id = data['channel_id']

        if not self._handshaking or self._potentially_reconnecting:
            # If we're done handshaking then we just need to update ourselves
            # If we're potentially reconnecting due to a 4014, then we need to differentiate
            # a channel move and an actual force disconnect
            if channel_id is None:
                # We're being disconnected so cleanup
                self._leaving.set()
                await self.disconnect()
            else:
                guild = self.guild
                self.channel = channel_id and guild and guild.get_channel(int(channel_id))
        else:
            self._voice_state_complete.set()

    async def connect(self, *, reconnect, timeout):
        async with self._lock:
            await super().connect(reconnect=reconnect, timeout=timeout)

    async def _disconnect(self):
        self._stop()
        self._connected.clear()

        try:
            if self.ws:
                await self.ws.close()

            await self.voice_disconnect()
        finally:
            self.cleanup()
            if self.socket:
                self.socket.close()

    async def disconnect(self, *, force=False):
        if not force:
            if not self.is_connected():
                return
            async with self._lock:
                await self._disconnect()
        else:
            await self._disconnect()

    async def move_to(self, channel):
        async with self._lock:
            await super().move_to(channel)
    
    async def reconnect(self, reconnect=True, timeout=10):
        """Disconnect forcefully from voice channel and connect it again
        
        Parameters
        ------------
        reconnect: :class:`bool`
            Reconnect when connection is failing.
        timeout: :class:`float`
            The timeout for the connection.
        """
        async with self._lock:
            await self.disconnect(force=True)
        await self.connect(reconnect=reconnect, timeout=timeout)

    # Playback controls

    async def _play_next_song(self):
        # If disconnected then do nothing.
        if not self.is_connected():
            return
        
        # Play the next song
        async with self._lock:
            track = self._playlist.get_next_track()
            if track:
                self._play(track, self._after)

        return track


    def register_after_callback(self, func: Callable[[Union[Exception, None], Union[Track, None]], Any]):
        """Register a callable function (can be coroutine function)
        for callback after player has done playing and play the next song or error occured.

        Parameters
        ------------
        func: Callable[[Union[:class:`Exception`, None], Union[:class:`Track`, None]], Any]
            a callable function (can be coroutine function) that accept 2 parameters: :class:`Exception`
            and :class:`Track`.
            That :class:`Exception` is for exception in the player (if error happened) and 
            :class:`Track` is for the next audio track. 
        
        Raises
        --------
        TypeError
            Not a callable function
        """
        if not callable(func):
            raise TypeError('Expected a callable, got %s' % type(func))
        self._after = func

    def add_track(self, track: Track):
        """Add a track to playlist
        
        Parameters
        -----------
        track: :class:`Track`
            Audio Track that we're gonna play.
        """
        self._playlist.add_track(track)

    def _play(self, track, after):
        if not self.encoder and not track.source.is_opus():
            self.encoder = opus.Encoder()

        self._player = MusicPlayer(track, self, after=after)
        self._player.start()

        # we are playing
        self._done.clear()

    async def play(self, track: Track):
        """Play a Track

        This function is automatically add track to playlist,
        even it still playing songs.
        
        Parameters
        -----------
        track: :class:`Track`
            Audio Track that we're gonna play.

        Raises
        -------
        NotConnected
            Not connected to voice
        TypeError
            "track" paramater is not :class:`Track`
        """
        if not self.is_connected():
            raise NotConnected('Not connected to voice.')

        if not isinstance(track, Track):
            raise TypeError('track must an Track not {0.__class__.__name__}'.format(track))

        async with self._lock:
            if self.is_playing():
                self._playlist.add_track(track)
                return
            self._playlist.add_track(track)
            self._play(track, self._after)

    async def play_track_from_pos(self, pos: int):
        """Play track from given pos
        
        Parameters
        -----------
        pos: :class:`int`
            Track position that we want to play.
        
        Raises
        -------
        NotConnected
            Not connected to voice
        TrackNotExist
            Given track position is not exist
        """
        if not self.is_connected():
            raise NotConnected('Not connected to voice.')
        async with self._lock:
            self._soft_stop()
            track = self._playlist.jump_to_pos(pos)
            self._play(track, self._after)

    def _stop(self):
        if self._player:
            self._player.stop()
            self._player.join()
            self._player = None

    def _soft_stop(self):
        if self._player:
            self._done.set()
            self._player.soft_stop()
            self._player = None

    async def stop(self):
        """Stop playing audio
        
        Raises
        -------
        MusicNotPlaying
            Not playing any audio
        """
        if not self.is_playing() or not self._player:
            raise MusicNotPlaying('Not playing any audio')
        async with self._lock:
            self._stop()

    async def pause(self, play_silence=True):
        """Pauses the audio playing.

        Parameters
        -----------
        play_silence: :class:`bool` (default: `True`)
            if `True` play silence audio.

        Raises
        -------
        MusicNotPlaying
            Not playing any audio     
        """

        if not self.is_playing() or not self._player:
            raise MusicNotPlaying('Not playing any audio')
        async with self._lock:
            self._player.pause(play_silence=play_silence)

    async def resume(self):
        """Resumes the audio playing.
        
        Raises
        -------
        MusicAlreadyPlaying
            Already playing audio
        MusicNotPlaying
            Not playing any audio
        """
        if self.is_playing():
            raise MusicAlreadyPlaying('Already playing audio')
        elif not self._player:
            raise MusicNotPlaying('Not playing any audio')
        async with self._lock:
            self._player.resume()
    
    async def seek(self, seconds: Union[int, float]):
        """Jump forward to specified durations
        
        Parameters
        -----------
        seconds: Union[:class:`int`, :class:`float`]
            Time to seek in seconds
        
        Raises
        -------
        MusicNotPlaying
            Not playing any audio
        """
        if not self.is_playing() or not self._player:
            raise MusicNotPlaying('Not playing any audio')
        async with self._lock:
            self._player.seek(seconds)

    async def rewind(self, seconds: Union[int, float]):
        """Jump back to specified durations
        
        Parameters
        -----------
        seconds: Union[:class:`int`, :class:`float`]
            Time to rewind in seconds

        Raises
        -------
        MusicNotPlaying
            Not playing any audio
        """
        if not self.is_playing() or not self._player:
            raise MusicNotPlaying('Not playing any audio')
        async with self._lock:
            self._player.rewind(seconds)

    def get_stream_durations(self) -> Union[float, None]:
        """Optional[:class:`float`]: Get current stream durations in seconds, if playing.
        """
        return self._player.get_stream_durations() if self._player else None

    async def next_track(self):
        """Play next track
        
        Raises
        -------
        NotConnected
            Not connected to voice.
        NoMoreSongs
            No more songs in playlist.
        """
        if not self.is_connected():
            raise NotConnected('Not connected to voice.')
        async with self._lock:
            self._soft_stop()
            track = self._playlist.get_next_track()
            if track is None:
                raise NoMoreSongs('no more songs in playlist')
            self._play(track, self._after)

    async def previous_track(self):
        """Play previous track
        
        Raises
        -------
        NotConnected
            Not connected a voice.
        NoMoreSongs
            No more songs in playlist.
        """
        if not self.is_connected():
            raise NotConnected('Not connected to voice.')
        async with self._lock:
            self._soft_stop()
            track = self._playlist.get_previous_track()
            if track is None:
                raise NoMoreSongs('no more songs in playlist')
            self._play(track, self._after)

    async def remove_track(self, track: Track):
        """Remove a track and stop the player (if given track same as playing track)
        
        Parameters
        -----------
        track: :class:`Track`
            A `Track` you want to remove
        
        Raises
        -------
        TrackNotExist
            Given track is not exist
        """
        if self.is_playing():
            _track = self._player.track
            if _track == track:
                # Skip to next track if same track
                try:
                    await self.next_track()
                except MusicClientException:
                    # Ignore if next track is not exist
                    pass
        async with self._lock:
            self._playlist.remove_track(track)

    async def remove_track_from_pos(self, pos: int):
        """Remove a track from given position and stop the player (if given pos same as playing track pos)

        Parameters
        -----------
        pos: :class:`int`
            Track position that we want to remove.

        Raises
        -------
        TrackNotExist
            Given track is not exist
        """
        track = self._playlist.get_track_from_pos(pos)
        if self.is_playing():
            _track = self._player.track
            if _track == track:
                try:
                    await self.next_track()
                except MusicClientException:
                    # Ignore if next track is not exist
                    pass
        async with self._lock:
            self._playlist.remove_track_from_pos(pos)

    async def remove_all_tracks(self):
        """Remove all tracks and stop the player (if playing)"""
        async with self._lock:
            if self.is_playing():
                self._stop()
            self._playlist.remove_all_tracks()

    # Track related

    @property
    def source(self):
        """Optional[:class:`MusicSource`]: The audio source being played, if playing."""
        return self._player.source if self._player else None
    
    @source.setter
    def source(self, value):
        raise NotImplementedError

    @property
    def track(self) -> Union[Track, None]:
        """Optional[:class:`Track`]: The audio track being played, if playing.
        """
        return self._player.track if self._player else None
