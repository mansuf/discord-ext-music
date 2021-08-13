import asyncio
import traceback
import threading

from typing import Callable, Any, Union
from discord.voice_client import VoiceClient
from discord import opus
from .playlist import Playlist
from .track import Track
from .player import MusicPlayer
from .utils.errors import MusicAlreadyPlaying, MusicNotPlaying, NoMoreSongs, NotConnected

# This class implement discord.voice_client.VoiceClient
# https://github.com/Rapptz/discord.py/blob/master/discord/voice_client.py#L175
# with music control (play, stop, pause, resume, seek, rewind)
# and playlist control (next, previous, jump_to, remove, remove_all, reset_pos)
class MusicClient(VoiceClient):
    def __init__(self, client, channel):
        super().__init__(client, channel)
        self._after = self._call_after

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

    async def _call_after(self, err, track):
        if err:
            print('Ignoring error %s: %s' % (err.__class__.__name__, str(err)))
            traceback.print_exception(type(err), err, err.__traceback__)
        _track = self._playlist.get_next_track()
        if _track:
            async with self._lock:
                self._play(_track, self._after)

    def register_after_callback(self, func: Callable[[Union[Exception, None], Union[Track, None]], Any]):
        """Register a callable function (can be coroutine function)
        for callback after player has done playing or error occured.

        Parameters
        ------------
        func: Callable[[Union[`Exception`, None], Union[`Track`, None]], Any]
            a callable function (can be coroutine function)
        
        Raises
        --------
        TypeError
            Not a callable function
        """
        if not callable(func):
            raise TypeError('Expected a callable, got %s' % type(func))
        self._after = func

    def add_track(self, track: Track):
        """Add a track to playlist"""
        self._playlist.add_track(track)

    def _play(self, track, after):
        if not self.encoder and not track.source.is_opus():
            self.encoder = opus.Encoder()

        self._player = MusicPlayer(track, self, after=after)
        self._player.start()

        # we are playing
        self._done.clear()

    async def play(self, track: Track):
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

    def _stop(self):
        if self._player:
            self._done.set()
            self._player.stop()
            self._player = None

    async def stop(self):
        if not self._player:
            raise MusicNotPlaying('MusicClient Not playing any audio')
        async with self._lock:
            self._stop()

    async def pause(self, play_silence=True):
        if not self.is_playing() or not self._player:
            raise MusicNotPlaying('MusicClient Not playing any audio')
        async with self._lock:
            self._player.pause(play_silence=play_silence)

    async def resume(self):
        if self.is_playing():
            raise MusicAlreadyPlaying('Already playing audio')
        elif not self._player:
            raise MusicNotPlaying('MusicClient Not playing any audio')
        async with self._lock:
            self._player.resume()
    
    async def seek(self, seconds: Union[int, float]):
        """Jump forward to specified durations"""
        if not self.is_playing() or not self._player:
            raise MusicNotPlaying('MusicClient Not playing any audio')
        async with self._lock:
            self._player.seek(seconds)

    async def rewind(self, seconds: Union[int, float]):
        """Jump back to specified durations"""
        if not self.is_playing() or not self._player:
            raise MusicNotPlaying('MusicClient Not playing any audio')
        async with self._lock:
            self._player.rewind(seconds)

    def get_stream_duration(self) -> float:
        return self._player.get_stream_durations() if self._player else None

    async def next_track(self):
        """Play next track"""
        if not self.is_connected():
            raise NotConnected('Not connected to voice.')
        async with self._lock:
            if self.is_playing():
                self._stop()
            track = self._playlist.get_next_track()
            if track is None:
                raise NoMoreSongs('no more songs in playlist')
            self._play(track, self._after)

    async def previous_track(self):
        """Play previous track"""
        if not self.is_connected():
            raise NotConnected('Not connected to voice.')
        async with self._lock:
            if self.is_playing():
                self._stop()
            track = self._playlist.get_previous_track()
            if track is None:
                raise NoMoreSongs('no more songs in playlist')
            self._play(track, self._after)

    async def jump_to_pos(self, pos: int):
        """Play track from given pos"""
        if not self.is_connected():
            raise NotConnected('Not connected to voice.')
        async with self._lock:
            if self.is_playing():
                self._stop()
            track = self._playlist.jump_to_pos(pos)
            self._play(track, self._after)

    async def remove_track(self, track: Track):
        """Remove a track"""
        if self.is_playing():
            _track = self._player.track
            if _track == track:
                # Skip to next track if same track
                await self.next_track()
        async with self._lock:
            self._playlist.remove_track(track)

    async def remove_track_from_pos(self, pos: int):
        """Remove a track from given position"""
        track = self._playlist.get_track_from_pos(pos)
        if self.is_playing():
            _track = self._player.track
            if _track == track:
                await self.next_track()
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
        return self._player.source if self._player else None
    
    @source.setter
    def source(self, value):
        raise NotImplementedError

    @property
    def track(self) -> Union[Track, None]:
        """Optional[:class:`Track`]: The audio track being played, if playing.
        """
        return self._player.track if self._player else None
