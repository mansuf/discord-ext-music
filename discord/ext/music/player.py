import sys
import logging
import time
import asyncio
import traceback

from discord.utils import maybe_coroutine
from discord.player import AudioPlayer

from .voice_source import Silence

log = logging.getLogger(__name__)

class MusicPlayer(AudioPlayer):
    def __init__(self, track, client):
        super().__init__(track.source, client)
        self._play_silence = False
        self.track = track
        self._silence = Silence()
        self._leaving = client._leaving
        self._done = client._done
        self._error = client._on_error
        
        # Client playlist
        self.playlist = client._playlist

        # Replacing thread name
        # MusicPlayer_{ChannelID}_{Track pos}_{Track hash}
        self.name = 'MusicPlayer_%s_%s_%s' % (
            client.channel.id,
            self.playlist.get_pos_from_track(track),
            id(track)
        )

        # For play the next song after done playing
        self.next_song = client._play_next_song

        # pre-play and post-play next song
        self.pre_func = client._pre_next
        self.post_func = client._post_next

        # For set_source()
        self._lock = client._lock

    def run(self):
        try:
            self._do_run()
        except Exception as exc:
            self._current_error = exc
            self.stop()
        finally:
            if not self._leaving.is_set() and self._connected.is_set():
                self._call_after()

    def _do_run(self):
        self.loops = 0
        self._start = time.perf_counter()

        # getattr lookup speed ups
        play_audio = self.client.send_audio_packet
        self._speak(True)

        while not self._end.is_set():
            # are we paused?
            if not self._resumed.is_set():
                # Check if we're allowed to play Silence audio
                if self._play_silence:
                    # Play opus encoded silence audio
                    play_audio(self._silence.read(), encode=False)

                    # Add delay to prevent overload CPU usage
                    time.sleep(0.02)
                    continue

                # wait until we aren't
                self._resumed.wait()
                continue

            # are we disconnected from voice?
            if not self._connected.is_set():

                # Checking if we are really leaving voice
                while not self._connected.is_set():
                    if self._leaving.is_set() and not self._connected.is_set():
                        # We're leaving voice, stopping player
                        self.stop()
                        return
                    else:
                        # Add delay to prevent overload CPU usage
                        time.sleep(0.02)
                        continue
                # reset our internal data
                self.loops = 0
                self._start = time.perf_counter()

            self.loops += 1
            data = self.source.read()

            if not data:
                self.stop()
                break

            play_audio(data, encode=not self.source.is_opus())
            next_time = self._start + self.DELAY * self.loops
            delay = max(0, self.DELAY + (next_time - time.perf_counter()))
            time.sleep(delay)

    def _handle_error(self):
        error = self._current_error

        if self._error:
            fut = asyncio.run_coroutine_threadsafe(maybe_coroutine(self._error, error), self.client.loop)
            exc = fut.exception()
            if exc:
                log.exception('Calling on player error function failed.')
                exc.__context__ = error
                traceback.print_exception(type(exc), exc, exc.__traceback__)
        elif error:
            msg = 'Exception in MusicPlayer thread {}'.format(self.name)
            log.exception(msg, exc_info=error)
            print(msg, file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__)

    def _call_after(self):
        # Check if MusicClient.stop() is called
        if self._done.is_set():
            self._handle_error()
            return

        # get the next track
        track = self.playlist.get_next_track()

        # Call pre-play next function
        if self.pre_func is not None:
            fut = asyncio.run_coroutine_threadsafe(maybe_coroutine(self.pre_func, track), self.client.loop)
            exc = fut.exception()
            if exc:
                log.exception('Calling the pre-play next track function failed.')
                exc.__context__ = exc
                traceback.print_exception(type(exc), exc, exc.__traceback__)

        # Play the next song
        fut = asyncio.run_coroutine_threadsafe(self.next_song(track), self.client.loop)
        exc = fut.exception()
        if exc:
            log.exception('Calling play next track failed.')
            exc.__context__ = exc
            traceback.print_exception(type(exc), exc, exc.__traceback__)

        # Call post-play next function
        if self.post_func is not None:
            fut = asyncio.run_coroutine_threadsafe(maybe_coroutine(self.post_func, track), self.client.loop)
            exc = fut.exception()
            if exc:
                log.exception('Calling the post-play next track function failed.')
                exc.__context__ = exc
                traceback.print_exception(type(exc), exc, exc.__traceback__)

        self._handle_error()

    def pause(self, *, update_speaking=True, play_silence=True):
        self._play_silence = play_silence
        super().pause(update_speaking=update_speaking)
    
    def resume(self, *, update_speaking=True):
        self._play_silence = False
        super().resume(update_speaking=update_speaking)

    def stop(self):
        super().stop()
        self.source.recreate()
        
    def _set_source(self, source):
        pass

    async def set_track(self, track):
        async with self._lock:
            self.pause(update_speaking=False)
            self.source = track.source
            self.track = track
            self.resume(update_speaking=False)

    def seek(self, seconds):
        self.pause(update_speaking=False)
        self.source.seek(seconds)
        self.resume(update_speaking=False)

    def rewind(self, seconds):
        self.pause(update_speaking=False)
        self.source.rewind(seconds)
        self.resume(update_speaking=False)

    def get_stream_durations(self):
        return self.source.get_stream_durations()
    