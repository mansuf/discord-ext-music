import threading
import av
from .io import LibAVIO

class LibAVStream:
    """A class represent LibAV Stream"""
    def __init__(self, url, format, codec, rate, seek=None) -> None:
        self.url = url
        # Will be used later
        self.kwargs = {
            "url": url,
            "format": format,
            "codec": codec,
            "rate": rate,
            "seek": seek
        }
        self.buffer = LibAVIO()
        self.pos = 0
        self.durations = 0
        self.stream = None
        self.output_stream = None
        self.muxer = None
        self.demuxer = None
        self._lock = threading.Lock()

        # Will be used in Decoder Stream
        self._stream_buffer = LibAVIO()

        # Iteration data LibAV
        self.iter_data = self._iter_av_packets()

    def reconnect(self, seek=None):
        # Speed up grab kwargs
        _seek_kwarg = self.kwargs.get('seek')
        format = self.kwargs.get('format')
        codec = self.kwargs.get('codec')
        rate = self.kwargs.get('rate')

        self.stream = av.open(self.url, 'r')
        self.durations = self.stream.duration
        _seek_durations = 0
        # If seek argument is defined in __init__()
        if _seek_kwarg:
            _seek_durations += _seek_kwarg
            # Delete seek argument, since we don't need it anyway
            self.kwargs.pop('seek')
        if seek:
            _seek_durations += seek
        # Begin the seek process
        if _seek_durations:
            self.stream.seek(int(_seek_durations * av.time_base), any_frame=True)

        # Change current stream durations
        self.pos += _seek_durations

        # Set up Encoder and Decoder
        self.demuxer = self.stream.demux(audio=0)
        self.muxer = av.open(self._stream_buffer, 'w', format=format)
        self.output_stream = self.muxer.add_stream(codec, rate=rate)
        
    def _close(self):
        if self.stream:
            self.stream.close()
        if self.muxer:
            self.muxer.close()
        self.output_stream = None
        self.demuxer = None
        self._stream_buffer = LibAVIO()

    def close(self):
        self._close()
        self.buffer = LibAVIO()
        self.iter_data.close()

    def _iter_av_packets(self, seek=None):
        self.reconnect(seek)
        while True:
            packet = next(self.demuxer, b'')

            # If stream is exhausted, close connection
            if not packet:
                self._close()
                return b''
            
            # If packet is corrupted, reconnect it
            if packet.is_corrupt:
                self._close()
                self.reconnect(self.pos)

            # According PyAV if demuxer sending packet with attribute dts with value None
            # that means demuxer is sending dummy packet.
            # If dummy packet is decoded it will flush the buffers.
            if packet.dts is None:
                packet.decode()
                self._close()
                return b''

            # Decode the packet
            frames = packet.decode()

            for frame in frames:
                self.pos = frame.time
                # https://github.com/PyAV-Org/PyAV/issues/281
                frame.pts = None
                new_packets = self.output_stream.encode(frame)
                self.muxer.mux(new_packets)
                yield self._stream_buffer.read()

    def seek(self, seconds: float):
        _seconds = 0
        with self._lock:
            if seconds < self.durations:
                pass
            elif seconds > self.durations:
                pass
            else:
                _seconds += seconds
            self.iter_data = self._iter_av_packets(_seconds)

    def read(self, n):
        data = next(self.iter_data, b'')
        self.buffer.write(data)
        return self.buffer.read(n)
