import threading
import av
import io
from .io import LibAVIO
from ...utils.errors import IllegalSeek, LibAVError

class LibAVAudioStream(io.RawIOBase):
    """A file-like class represent LibAV audio-only stream"""
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
        self._stopped = threading.Event()

        # Will be used in Decoder Stream
        self._stream_buffer = LibAVIO()

        # Check connection
        self._check_connection(url)

        # Iteration data LibAV
        self.iter_data = self._iter_av_packets()

    def _check_connection(self, url):
        try:
            stream = av.open(url, 'r')
            self.durations = stream.duration
            stream.close()
        except av.error.FFmpegError as e:
            raise LibAVError(str(e)) from None

    def reconnect(self, seek=None):
        # Speed up grab kwargs
        _seek_kwarg = self.kwargs.get('seek')
        format = self.kwargs.get('format')
        codec = self.kwargs.get('codec')
        rate = self.kwargs.get('rate')

        self.stream = av.open(self.url, 'r')
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
        self._stream_buffer = LibAVIO()
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
        self._stopped.set()

    def is_closed(self):
        return self._stopped.is_set()

    def close(self):
        self._close()
        self.buffer = LibAVIO()
        self.iter_data.close()

    def _iter_av_packets(self, seek=None):
        self.reconnect(seek)
        while True:
            try:
                packet = next(self.demuxer, b'')
            except av.error.FFmpegError:
                # Fail to get packet such as invalidated session, etc

                # Close the stream and muxer to stop PyAV yelling some errors
                self.stream.close()
                self.muxer.close()

                # Reconnect the stream
                self.reconnect(self.pos)
                continue

            # If stream is exhausted, close connection
            if not packet:
                self._close()
                return b''
            
            # If packet is corrupted, reconnect it
            if packet.is_corrupt:
                # Close the stream and muxer to stop PyAV yelling some errors
                self.stream.close()
                self.muxer.close()

                # Reconnect the stream
                self.reconnect(self.pos)
                continue

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
        if self.durations is None:
            raise IllegalSeek('current stream doesn\'t support seek')
        with self._lock:
            if seconds < 0:
                self.close()
            elif seconds > self.durations:
                self.close()
            if self.stream:
                self.stream.seek(seconds)
            self.pos = seconds

    def tell(self):
        return self.pos

    def read(self, n=-1):
        data = next(self.iter_data, b'')
        self.buffer.write(data)
        return self.buffer.read(n)
