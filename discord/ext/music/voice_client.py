import asyncio
import traceback
import threading
import os

from typing import Callable, Any, Union
from discord.voice_client import VoiceClient
from .opus_encoder import get_opus_encoder
from .equalizer import Equalizer
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

_OpusEncoder = get_opus_encoder(os.environ.get('OPUS_ENCODER'))
__all__ = (
    'MusicClient',
)

class MusicClient(VoiceClient):
    """Same like :class:`discord.VoiceClient` but with playback controls for music.
    
    Each coroutine functions are thread-safe.

    You usually don't create these, you can get it from :meth:`discord.VoiceChannel.connect`

    Warning
    --------
    It is important to add parameter ``cls`` with value :class:`MusicClient` to :meth:`discord.VoiceChannel.connect`,
    otherwise you wont get these features. For example:

    .. code-block:: python3
        
        # Use this method
        music_client = await voice_channel.connect(cls=MusicClient)

        # But not this method
        music_client = await voice_channel.connect()
        
    """
    def __init__(self, client, channel):
        super().__init__(client, channel)
        self._pre_next = None
        self._post_next = None
        self._eq = None
        self._volume = None
        self._on_disconnect = None
        self._on_error = None

        # Will be used for _stop()
        self._done = asyncio.Event()
        
        # This will be used if bot is leaving voice channel
        self._leaving = threading.Event()

        # Playlist to store tracks
        self._playlist = Playlist()

        # Will be used for music controls
        self._lock = asyncio.Lock()

    def on_disconnect(self, func: Callable[[], Any]):
        """A decorator that register a callable function as hook when disconnected

        Note
        -----
        The function must be coroutine / async, otherwise it will raise error.
        The function must be not take any parameters.

        Parameters
        -----------
        func
            a callable function (must be a coroutine function)
        
        Raises
        -------
        TypeError
            The function is not coroutine or async
        """
        if not asyncio.iscoroutinefunction(func):
            raise TypeError('The function is not coroutine or async')
        self._on_disconnect = func

    def on_player_error(self, func: Callable[[Exception], Any]):
        """A decorator that register a callable function as hook when player encountered error.

        The function can be normal function or coroutine (async) function.

        Parameters
        -----------
        func: Callable[[:class:`Exception`], Any]
            a callable function (can be a coroutine function)
        
        Raises
        -------
        TypeError
            The function is not coroutine or async
        """
        self._on_error = func

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
                if self._on_disconnect is not None:
                    await self._on_disconnect()
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
        """Disconnects this voice client from voice."""
        if not force:
            if not self.is_connected():
                return
            async with self._lock:
                await self._disconnect()
        else:
            await self._disconnect()

    async def move_to(self, channel):
        """Moves you to a different voice channel.

        Parameters
        -----------
        channel: :class:`discord.VoiceChannel`
            The channel to move to. Must be a voice channel.
        """
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

    @property
    def playlist(self):
        """:class:`Playlist`: Return current playlist"""
        return self._playlist
    
    async def set_playlist(self, playlist: Playlist, stop_player: bool=False):
        """Replace current playlist with given playlist
        
        Parameters
        -----------
        playlist: :class:`Playlist`
            A playlist that want to be setted
        stop_player: :class:`bool`
            Stop the player when changing playlist (if playing) and play current track from new playlist.
        
        Raises
        -------
        TypeError
            "playlist" parameter is not :class:`Playlist`
        """
        if stop_player:
            try:
                await self.stop()
            except MusicNotPlaying:
                pass
        if not isinstance(playlist, Playlist):
            raise TypeError('playlist must an Playlist not {0.__class__.__name__}'.format(playlist))

        self._playlist = playlist
        async with self._lock:
            self._play(playlist.get_current_track())

    async def _play_next_song(self, track):
        # If disconnected then do nothing.
        if not self.is_connected():
            return
        
        # Play the next song
        async with self._lock:
            if track:
                self._play(track)

    def before_play_next(self, func: Callable[[Union[Track, None]], Any]):
        """A decorator that register callable function (can be coroutine function) as a pre-play next track
        
        This is useful for checking a streamable url or any type of set up required.

        The ``func`` callable must accept 1 parameter :class:`Track` that is the next track 
        that want to be played.

        Parameters
        -----------
        func: Callable[[Union[:class:`Track`, ``None``]], Any]
            The callable function to register as pre-play next track.

        Raises
        --------
        TypeError
            Not a callable function
        """
        if not callable(func):
            raise TypeError('Expected a callable, got %s' % type(func))
        self._pre_next = func

    def after_play_next(self, func: Callable[[Union[Track, None]], Any]):
        """A decorator that register callable function (can be coroutine function) as a post-play next track
        
        This is useful for sending announcement or any type of clean up required.

        The ``func`` callable must accept 1 parameter :class:`Track` that is the next track 
        that want to be played.

        Parameters
        -----------
        func: Callable[[Union[:class:`Track`, ``None``]], Any]
            The callable function to register as post-play next track.

        Raises
        --------
        TypeError
            Not a callable function
        """
        if not callable(func):
            raise TypeError('Expected a callable, got %s' % type(func))
        self._post_next = func

    def add_track(self, track: Track):
        """Add a track to playlist
        
        Parameters
        -----------
        track: :class:`Track`
            Audio Track that we're gonna add to playlist.
        """
        self._playlist.add_track(track)

    def _play(self, track):
        if not self.encoder and not track.source.is_opus():
            self.encoder = _OpusEncoder()

        # Apply equalizer
        if self._eq:
            try:
                track.source.set_equalizer(self._eq)
            except NotImplementedError:
                pass
        
        # Apply volume
        if self._volume:
            try:
                track.source.set_volume(self._volume)
            except NotImplementedError:
                pass

        self._player = MusicPlayer(track, self)
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
            self.add_track(track)
            if not self.is_playing():
                self._play(track)

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
            self._stop()
            track = self._playlist.jump_to_pos(pos)
            self._play(track)

    def _stop(self):
        if self._player:
            self._done.set()
            self._player.stop()
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
        play_silence: :class:`bool`
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
            self._stop()
            track = self._playlist.get_next_track()
            if track is None:
                raise NoMoreSongs('no more songs in playlist')
            self._play(track)

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
            self._stop()
            track = self._playlist.get_previous_track()
            if track is None:
                raise NoMoreSongs('no more songs in playlist')
            self._play(track)

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
    def equalizer(self):
        """Optional[:class:`Equalizer`]: Return current equalizer music source being played (if playing)."""
        return self.source.equalizer if self.source else None

    def set_equalizer(self, equalizer: Equalizer):
        """Set equalizer for music source

        Note
        -----
        This will apply equalizer to all music sources to this playlist.
        music sources that don't support equalizer or volume adjust will be ignored.

        Parameters
        -----------
        equalier: :class:`Equalizer`
            Equalizer that want to be setted in music source

        Raises
        -------
        MusicNotPlaying
            Not playing any audio
        MusicClientException
            current music source does not support equalizer
        """
        if not self.is_playing():
            raise MusicNotPlaying('Not playing any audio')
        if self.is_playing():
            try:
                self.source.set_equalizer(equalizer)
            except NotImplementedError:
                pass
        self._eq = equalizer

    @property
    def volume(self):
        """Optional[:class:`float`]: Return current volume music source being played (if playing)."""
        return self.source.volume if self.source else None

    def set_volume(self, volume: float):
        """Set volume for music source for this channel.

        Note
        -----
        This will apply volume to all music sources to this playlist.
        music sources that don't support equalizer or volume adjust will be ignored.
        
        Parameters
        -----------
        volume: :class:`float`
            Volume that want to be setted in music source
        
        Raises
        -------
        MusicNotPlaying
            Not playing any audio
        MusicClientException
            current music source does not support volume adjust
        """
        if not self.is_playing():
            raise MusicNotPlaying('Not playing any audio')
        if self.is_playing():
            try:
                self.source.set_volume(volume)
            except NotImplementedError:
                pass
        self._volume = volume

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
