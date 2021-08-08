import logging
import time
import asyncio

from discord.player import AudioPlayer
from .voice_source import Silence

log = logging.getLogger(__name__)

class _Player(AudioPlayer):
    def __init__(self, source, client, *, after=None):
        super().__init__(source, client, after=after)
        self._play_silence = False
        self._silence = Silence()

        # For _set_source()
        self._lock = asyncio.Lock()

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
                # wait until we are connected
                self._connected.wait()
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

    def pause(self, *, update_speaking=True, play_silence=True):
        self._play_silence = play_silence
        super().pause(update_speaking=update_speaking)
    
    def resume(self, *, update_speaking=True):
        self._play_silence = False
        super().resume(update_speaking=update_speaking)

    def _set_source(self, source):
        pass

    async def set_source(self, source):
        async with self._lock:
            self.pause(update_speaking=False)
            self.source = source
            self.resume(update_speaking=False)

class MusicPlayer:
    def __init__(self, source, client, *, after=None) -> None:
        pass