import audioop
import random
import threading
import time
import av
import io
import queue
from discord.oggparse import OggStream
from discord.opus import Encoder as OpusEncoder
from typing import Any, Generator, Union
from .legacy import MusicSource, EQ_OK, PCMEqualizer, EqualizerError

class BufferIO(io.RawIOBase):
    def __init__(self):
        self.buf = bytearray()
        self.q = queue.Queue()
        self.pos = 0
        self.lock = threading.Lock()

    def read(self, n=-1):
        with self.lock:
            if n <= 0:
                data = self.buf[0:]
                del self.buf[0:]
            else:
                data = self.buf[:n]
                del self.buf[:n]
        return bytes(data)

    def write(self, buf):
        with self.lock:
            self.buf += buf
            self.pos += len(buf)
        return len(buf)
    
    def flush(self) -> None:
        pass

    def tell(self) -> int:
        return self.pos

    def getvalue(self):
        return self.buf

    def truncate(self, __size: int):
        pass

    def writable(self) -> bool:
        return True

# PCM 20ms bytes size
REQUIRED_SIZE = OpusEncoder.FRAME_SIZE

class _LibAVStream(threading.Thread):
    # This stream reading is done by another thread, why ?.
    # Because, for some reason if PyAV stream in current thread it will
    # cause too much delay (the process is blocked with async selectors i think ?).
    # Even using QueueWorker its not enough, still blocked.
    # I looked for same issues in PyAV github repository and there is none.
    # So the only solution is create PyAV stream in another thread.

    def __init__(self, source, volume):
        threading.Thread.__init__(self, daemon=True)
        self.input = av.open(source, 'r')
        self.stream = self.input.demux(audio=0)
        self.volume = max(volume, 0.0) if volume is not None else None
        self.durations = 0
        self.eq = None
        self.buffer = BufferIO()
        self._start = threading.Event()
        self.end = threading.Event()
        self._destroy = threading.Event()
        self.suspend = threading.Semaphore(20)
        self.pos = 0
        self.muxer = av.open(self.buffer, 'w', format='ogg')
        self.output_stream = self.muxer.add_stream('libopus', rate=48000)
        self.output_stream.codec_context.thread_count = 1
        self.output_stream.codec_context.thread_type = 'AUTO'

    def run(self):
        while True:
            # If self.destroy is called()
            if self._destroy.is_set():
                self.end.set()
                return
            packet = next(self.stream, b'')
            # If stream is exhausted
            if not packet:
                return
            # According PyAV if demuxer sending packet with attribute dts with value None
            # that means demuxer is sending dummy packet.
            # If dummy packet is decode it will flush the buffers.
            # if packet.dts is None:
            #     packet.decode()
            #     self.end.set()
            #     return
            # Decode the packet
            frames = packet.decode()

            # volume = None
            # eq = None
            # # If volume adjuster is enabled
            # # then convert it to PCM bytes 
            # # because volume cannot be adjust in opus encoded
            # if self.volume is not None:
            #     volume = io.BytesIO()
            #     pcm_encoder = av.open(volume, 'w', format='s16le')
            #     pcm_stream = pcm_encoder.add_stream('pcm_s16le', rate=48000)
            #     for frame in frames:
            #         # https://github.com/PyAV-Org/PyAV/issues/281
            #         frame.pts = None
            #         packets = pcm_stream.encode(frame)
            #         pcm_encoder.mux(packets)
            #     pcm_encoder.close()
            #     volume.seek(0, 0)
            
            # # If equalizer is enabled
            # # then convert it to PCM bytes
            # # Because equalizer cannot be done in opus encoded
            # if self.eq is not None:
            #     eq = io.BytesIO(volume.read()) if volume is not None else io.BytesIO()
            #     pcm_encoder = av.open(eq, 'w', format='s16le')
            #     pcm_stream = pcm_encoder.add_stream('pcm_s16le', rate=48000)
            #     for frame in frames:
            #         # https://github.com/PyAV-Org/PyAV/issues/281
            #         frame.pts = None
            #         packets = pcm_stream.encode(frame)
            #         pcm_encoder.mux(packets)
            #     pcm_encoder.close()
            #     eq.seek(0, 0)
            
            # if eq is not None:
            #     pcm_decoder = av.open(eq, 'r', format='s16le')
            #     for packet in pcm_decoder.demux(audio=0):
            #         pcm_frames = packet.decode()
            #         for pcm_frame in pcm_frames:
            #             # https://github.com/PyAV-Org/PyAV/issues/281
            #             pcm_frame.pts = None
            #             pcm_packets = self.output_stream.encode(pcm_frame)
            #             self.muxer.mux(pcm_packets)
            #     pcm_decoder.close()
            # elif volume is not None:
            #     pcm_decoder = av.open(volume, 'r', format='s16le')
            #     for packet in pcm_decoder.demux(audio=0):
            #         pcm_frames = packet.decode()
            #         for pcm_frame in pcm_frames:
            #             # https://github.com/PyAV-Org/PyAV/issues/281
            #             pcm_frame.pts = None
            #             pcm_packets = self.output_stream.encode(pcm_frame)
            #             self.muxer.mux(pcm_packets)
            #     pcm_decoder.close()
            # else:
            for frame in frames:
                # https://github.com/PyAV-Org/PyAV/issues/281
                frame.pts = None
                new_packets = self.output_stream.encode(frame)
                self.muxer.mux(new_packets)
            self._start.set()
            self.suspend.acquire()

    def destroy(self):
        self._destroy.set()

    def read(self, n):
        while True:
            # Wait until data is buffered
            self._start.wait()

            # Is the stream is over ?
            if self.end.is_set():
                # Return empty bytes to signal that we're done streaming
                return b''
            
            # Read the stream
            data = self.buffer.read(n)
            self.suspend.release()

            # If the buffered stream is not showing data.
            # in case: delay, then re-reading stream until it get the data
            if not data:
                continue

            return data

class LibAVAudio(MusicSource):
    """
    Represents libav audio stream from FFmpeg libraries.
    This audio stream works like FFmpeg but it embedded into python.

    For now there is no volume adjuster and equalizer, because some problems.

    Note
    ------
    You must have `pyav` installed in order this to work.

    Parameters
    ------------
    source: Union[:class:`str`, :class:`io.BufferedIOBase`]
        The input that libav will take and convert to Opus bytes.
    """
    def __init__(
        self,
        source: Union[str, io.BufferedIOBase]
    ):
        self._input = _LibAVStream(source, None)
        self._stream = OggStream(self._input).iter_packets()
        self._first_run = False

    def is_opus(self):
        return True

    def read(self):
        if not self._first_run:
            self._input.start()
            self._first_run = True
        return next(self._stream, b'')

        
        