import av
from .stream import LibAVAudioStream
from ..legacy import MusicSource
from discord.oggparse import OggStream

__all__ = (
    'LibAVAudio', 'LibAVOpusAudio'
)

class LibAVAudio(MusicSource):
    """Represents embedded FFmpeg libraries audio source."""
    def is_opus(self):
        # This must return True
        # Otherwise it will encode to opus codec and caused crash
        # (Segmentation Fault)
        return True

# For some reason, LibAVStream.read() with libopus codec
# did not returning data sometimes.
class _OpusStream(LibAVAudioStream):
    def __init__(self, url) -> None:
        super().__init__(
            url,
            'ogg',
            'libopus',
            48000
        )
    
    def read(self, n):
        while True:
            data = super().read(n)
            if self.is_closed():
                return b''
            elif not data:
                continue
            return data

class LibAVOpusAudio(LibAVAudio):
    """Represents embedded FFmpeg libraries Opus audio source.

    There is no volume adjuster and equalizer for now, 
    because some problems.

    Parameters
    ------------
    url_or_file: :class:`str`
        Valid URL or file location
    
    Attributes
    ------------
    url: :class:`str`
        Valid URL or file location
    stream: :class:`_OpusStream`
        a file-like object that returning ogg opus encoded data

    Raises
    --------
    IllegalSeek
        current stream doesn't support seek() operations
    """
    def __init__(self, url_or_file: str) -> None:
        self.url = url_or_file
        self.stream = _OpusStream(url_or_file)
        self._ogg_stream = OggStream(self.stream).iter_packets()
    
    def recreate(self):
        self.stream = _OpusStream(self.url)
        self._ogg_stream = OggStream(self.stream).iter_packets()

    def read(self):
        return next(self._ogg_stream, b'')

    def get_stream_durations(self):
        return self.stream.tell()

    def seek(self, seconds: float):
        self.stream.seek(self.stream.pos + seconds)
    
    def rewind(self, seconds: float):
        self.stream.seek(self.stream.pos - seconds)

    def cleanup(self):
        return self.stream.close()