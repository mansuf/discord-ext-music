import asyncio
import discord
import logging
import sys
import nacl.secret
import struct
import time
import traceback
from discord import opus
from .voice_client import MusicClient
from .voice_source import MusicSource, Silence
from .worker import QueueWorker
from .equalizer import Equalizer

log = logging.getLogger(__name__)

class MusicPlayer:
    """
    Play music asynchronously
    """

    DELAY = opus.Encoder.FRAME_LENGTH / 1000.0

    def __init__(
        self,
        source: MusicSource,
        client: MusicClient,
        worker: QueueWorker,
        *,
        after=None,
        destroy_on_disconnect=False
    ):
        self.secret_key = client.secret_key
        self.client = client
        self.sequence = 0
        self.timestamp = 0
        self.source = source
        self._connection = client._voice_conn
        self._endpoint_ip = client.endpoint_ip
        self._endpoint_port = client.voice_port
        self._worker = worker
        self._loop = client.loop
        self._lite_nonce = 0
        self._connected = client._connected
        self._start_time = 0
        self._pause_time = 0
        self._end = asyncio.Event()
        self._resumed = asyncio.Event()
        self._paused = asyncio.Event()
        self._played = asyncio.Event()
        self._silence = asyncio.Event()
        # we are not paused
        self._resumed.set()
        self._destroy_on_dc = destroy_on_disconnect

        if after is not None and asyncio.iscoroutinefunction(after) or not callable(after):
            raise TypeError('Expected a callable or coroutine function for the "after" parameter.')

        self.after = after
        self.encoder = opus.Encoder()
        self._player = None
        self._current_error = None

    def checked_add(self, attr, value, limit):
        val = getattr(self, attr)
        if val + value > limit:
            setattr(self, attr, 0)
        else:
            setattr(self, attr, val + value)

    def _wrap_packet(self, data):
        header = bytearray(12)

        # Formulate rtp header
        header[0] = 0x80
        header[1] = 0x78
        struct.pack_into('>H', header, 2, self.sequence)
        struct.pack_into('>I', header, 4, self.timestamp)
        struct.pack_into('>I', header, 8, self.ssrc)

        encrypt_packet = getattr(self, '_encrypt_' + self.mode)
        return encrypt_packet(header, data)

    def _encrypt_xsalsa20_poly1305(self, header, data):
        box = nacl.secret.SecretBox(bytes(self.secret_key))
        nonce = bytearray(24)
        nonce[:12] = header

        return header + box.encrypt(bytes(data), bytes(nonce)).ciphertext

    def _encrypt_xsalsa20_poly1305_suffix(self, header, data):
        box = nacl.secret.SecretBox(bytes(self.secret_key))
        nonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)

        return header + box.encrypt(bytes(data), nonce).ciphertext + nonce

    def _encrypt_xsalsa20_poly1305_lite(self, header, data):
        box = nacl.secret.SecretBox(bytes(self.secret_key))
        nonce = bytearray(24)

        nonce[:4] = struct.pack('>I', self._lite_nonce)
        self.checked_add('_lite_nonce', 1, 4294967295)

        return header + box.encrypt(bytes(data), bytes(nonce)).ciphertext + nonce[:4]

    def _get_audio_packet(self, source):
        self.checked_add('sequence', 1, 65535)

        # Read audio source
        if source.is_async():
            coro = source.read()
            fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
            data = fut.result()
        else:
            data = source.read()

        # If audio source is not opus encode it
        if not self.source.is_opus():
            encoded_data = self.encoder.encode(data, self.encoder.SAMPLES_PER_FRAME)
        else:
            encoded_data = data
    
        # Wrap the audio packet
        packet = self._wrap_packet(encoded_data)
        return packet

    async def _speak(self, speaking: bool):
        try:
            await self.client.ws.speak(speaking)
        except Exception as e:
            log.info('Speaking call in player failed: %s', e)

    async def _process_silence(self):
        reader, writer = self._connection
        silence = Silence()
        while True:
            # Wait until is set
            await self._silence.wait()

            data = await self._worker.submit(lambda: self._get_audio_packet(silence))
            writer.write(data)

    async def _process(self):
        # getattr lookup speed ups
        reader, writer = self._connection
        source = self.source

        self.loops = 0
        self.durations = 0
        self._start_time = time.perf_counter()
        await self._speak(True)

        while self._played.is_set():
            # are we paused?
            if not self._resumed.is_set():

                # Set pause
                self._paused.set()

                # wait until we aren't
                await self._resumed.wait()

                # Unset pause
                self._paused.clear()
                continue

            # are we disconnected from voice?
            if not self._connected.is_set():
                # Stop the player
                if self._destroy_on_dc:
                    break

                # wait until we are connected
                await self._connected.wait()

                # reset our internal data
                self.loops = 0
                self._start = time.perf_counter()

            self.loops += 1
            self.durations += 0.020 # 20ms
            data = await self._worker.submit(lambda: self._get_audio_packet(source))
            
            if not data:
                break

            writer.write(data)
            self.checked_add('timestamp', opus.Encoder.SAMPLES_PER_FRAME, 4294967295)

            # Adapted from discord.js 
            # https://github.com/discordjs/discord.js/blob/v12/src/client/voice/dispatcher/StreamDispatcher.js#L234
            # delay = self.DELAY + self.loops * self.DELAY
            next_time = self._start_time + self.DELAY * self.loops
            delay = max(0, self.DELAY + (next_time - time.perf_counter()))
            await asyncio.sleep(delay)

        # Flush the buffer
        await writer.drain()

    async def _call_after(self):
        pass

    async def _run(self):
        # Wait until self.play() is called
        await self._played.wait()
        after = self.after

        try:
            await self._process()
        except Exception as e:
            self._current_error = e
        else:
            # Stop the player
            self._end.set()
            self._played.clear()
            self._paused.clear()

            # Change speak state to False
            await self._speak(False)

    async def play(self):
        if self._played.is_set():
            raise discord.ClientException('Already playing audio')
        

    async def stop(self):
        # Stop the player
        self._played.clear()

        # Wait until player is stopped
        await self._end.wait()

        # set pause event to False
        self._paused.clear()

        # Change speak state to False
        await self._speak(False)
    
    async def pause(self, play_silence=True):
        # Set resumed to False
        self._resumed.clear()

        if play_silence:
            # Play silence
            # https://discord.com/developers/docs/topics/voice-connections#voice-data-interpolation
            self._silence.set()

        # Wait until _process is paused
        await self._paused.wait()

        # Change speak state to False
        await self._speak(False)

    async def resume(self):
        # stop silence process
        self._silence.clear()

        # resume the player
        self._resumed.set()

        # Change speak state to True
        await self._speak(True)


