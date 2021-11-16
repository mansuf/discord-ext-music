import io
from ..legacy import MusicSource, RawPCMAudio
from discord.opus import _OpusStruct
from discord.oggparse import OggStream

# Try to import LibAVAudioStream
try:
    from .stream import LibAVAudioStream
    AV_OK = True
except ImportError as e:
    msg = str(e)
    # Find error "cannot allocate memory in static TLS block" in ARM-based CPU
    if 'cannot allocate memory in static TLS block' in msg:
        lib = msg.replace(': cannot allocate memory in static TLS block', '')

        # Throw the error and tell the user to add this to Enviroments
        # Because we can't fix this inside python
        raise ImportError('Cannot import av, do this command "export LD_PRELOAD=%s" to fix this' % lib) from None

    AV_OK = False
    # Try to create LibAVAudioStream without methods
    class LibAVAudioStream(io.RawIOBase):
        pass

__all__ = (
    'LibAVOpusAudio', 'LibAVPCMAudio'
)

class LibAVOpusAudio(MusicSource):
    """Represents embedded FFmpeg-based Opus audio source.

    Warning
    --------
    You must have `av`_ installed, otherwise it didn't work.

    .. _av: https://pypi.org/project/av/

    Parameters
    ------------
    url_or_file: :class:`str`
        Valid URL or file location
    
    Attributes
    ------------
    url: :class:`str`
        Valid URL or file location
    stream: :class:`io.RawIOBase`
        a file-like object that returning ogg opus encoded data

    Raises
    --------
    :class:`LibAVError`
        Something happened when opening connection stream url.
    """
    def __init__(self, url_or_file: str) -> None:
        super().__init__()
        self.url = url_or_file

        # Will be used later
        self.__stream_kwargs__ = {
            'url': url_or_file,
            'format': 'ogg',
            'codec': 'libopus',
            'rate': 48000,
            'mux': True
        }

        self.stream = LibAVAudioStream(**self.__stream_kwargs__)
        self._ogg_stream = OggStream(self.stream).iter_packets()
    
    def recreate(self):
        self.stream.close()
        self.stream = LibAVAudioStream(**self.__stream_kwargs__)
        self._ogg_stream = OggStream(self.stream).iter_packets()

    def is_opus(self):
        return True

    def set_volume(self, volume):
        raise NotImplementedError
    
    def set_equalizer(self, equalizer):
        raise NotImplementedError

    def read(self):
        return next(self._ogg_stream, b'')

    def get_stream_durations(self):
        return self.stream.tell()

    def seekable(self):
        return True

    def seek(self, seconds: float):
        self.stream.seek(self.stream.pos + seconds)
    
    def rewind(self, seconds: float):
        self.stream.seek(self.stream.pos - seconds)

    def cleanup(self):
        return self.stream.close()

class LibAVPCMAudio(RawPCMAudio):
    """Represents embedded FFmpeg-based audio source producing pcm packets.

    Warning
    --------
    You must have `av`_ installed, otherwise it didn't work.

    .. _av: https://pypi.org/project/av/

    Parameters
    ------------
    url_or_file: :class:`str`
        Valid URL or file location
    
    Attributes
    ------------
    url: :class:`str`
        Valid URL or file location
    stream: :class:`io.RawIOBase`
        a file-like object that returning pcm packets.

    Raises
    --------
    :class:`LibAVError`
        Something happened when opening connection stream url.
    """
    def __init__(self, url_or_file: str) -> None:
        self.url = url_or_file

        # Will be used later
        self.__stream_kwargs__ = {
            'url': url_or_file,
            'format': 's16le',
            'codec': 'pcm_s16le',
            'rate': 48000,
            'mux': False
        }
        stream = LibAVAudioStream(**self.__stream_kwargs__)
        super().__init__(stream)
    
    def recreate(self):
        self.stream.close()
        self.stream = LibAVAudioStream(**self.__stream_kwargs__)

    def get_stream_durations(self):
        return self.stream.tell()

    def seek(self, seconds: float):
        self.stream.seek(self.stream.pos + seconds)
    
    def rewind(self, seconds: float):
        self.stream.seek(self.stream.pos - seconds)

    def cleanup(self):
        return self.stream.close()