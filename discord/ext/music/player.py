import sys
import logging
import threading
import time
import asyncio
import traceback

from discord.player import AudioPlayer
from .voice_source import Silence

log = logging.getLogger(__name__)

class MusicPlayer(AudioPlayer):
    def __init__(self, track, client, *, after=None):
        super().__init__(track.source, client, after=after)
        self._play_silence = False
        self.track = track
        self._silence = Silence()
        self._leaving = client._leaving
        self._done = client._done

        # For play the next song after done playing
        self.next_song = client._play_next_song

        # Used for self.soft_stop()
        self._soft_stop = False

        # For set_source()
        self._lock = client._lock

    def run(self):
        try:
            self._do_run()
        except Exception as exc:
            self._current_error = exc
            self.stop()
        finally:
            if not self._soft_stop:
                self.source.cleanup()
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

    def _call_after(self):
        error = self._current_error

        # Check if MusicClient.stop() is called
        if self._done.is_set():
            if error:
                msg = 'Exception in voice thread {}'.format(self.name)
                log.exception(msg, exc_info=error)
                print(msg, file=sys.stderr)
                traceback.print_exception(type(error), error, error.__traceback__)
            return

        # Play the next song
        fut = asyncio.run_coroutine_threadsafe(self.next_song(), self.client.loop)
        track = fut.result()

        if self.after is not None:
            # Check if after function is coroutine or not
            if asyncio.iscoroutinefunction(self.after):
                fut = asyncio.run_coroutine_threadsafe(self.after(error, track), self.client.loop)
                exc = fut.exception()
                if exc:
                    log.exception('Calling the after function failed.')
                    exc.__context__ = error
                    traceback.print_exception(type(exc), exc, exc.__traceback__)
                return
            try:
                self.after(error, track)
            except Exception as exc:
                log.exception('Calling the after function failed.')
                exc.__context__ = error
                traceback.print_exception(type(exc), exc, exc.__traceback__)
        elif error:
            msg = 'Exception in voice thread {}'.format(self.name)
            log.exception(msg, exc_info=error)
            print(msg, file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__)

    def pause(self, *, update_speaking=True, play_silence=True):
        self._play_silence = play_silence
        super().pause(update_speaking=update_speaking)
    
    def resume(self, *, update_speaking=True):
        self._play_silence = False
        super().resume(update_speaking=update_speaking)

    def soft_stop(self):
        """Stop the player but not the ``MusicSource``

        `MusicSource` will be restarted from zero using `recreate()` method
        
        This will be used in:
        - `MusicClient.play_track_from_pos()`
        - `MusicClient.next_track()`
        - `MusicClient.previous_track()`
        """
        self._soft_stop = True

        # Stop the player
        self.stop()

        # Wait until it terminates
        self.join()
        
        # Start from zero
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
    