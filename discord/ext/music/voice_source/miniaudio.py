import asyncio
import io
from .legacy import RawPCMAudio
from ..utils.errors import *

# Try to import miniaudio module
try:
    import miniaudio
except ImportError:
    raise MiniaudioError('miniaudio not installed') from None

class MP3toPCMAudio(RawPCMAudio):
    """
    Represents mp3 to PCM audio source.

    This audio source will convert mp3 to pcm format (16-bit 48KHz).

    Note
    ------
    When you initiate this class, the audio data will automatically coverted to pcm.
    This may cause all asynchronous process is blocked by this process.
    If you want to avoid this, use :class:`MP3toPCMAudio.from_data` or 
    :class:`MP3toPCMAudio.from_file`.

    Parameters
    ------------
    data: :class:`bytes`
        MP3 bytes data
    volume: :class:`float`
        Set initial volume for AudioSource
    kwargs:
        These parameters will be passed in :class:`RawPCMAudio`

    Attributes
    -----------
    stream: :term:`py:file object`
        A file-like object that reads byte data representing raw PCM.

    Raises
    --------
    InvalidMP3
        The audio data is not mp3 format
    """
    def __init__(self, data: bytes, volume: float=0.5, **kwargs):
        converted = kwargs.get('converted')
        if not converted:
            decoded_data = self._decode(data)
        else:
            kwargs.pop('converted')
            decoded_data = data
        super().__init__(io.BytesIO(decoded_data), volume, **kwargs)

    @classmethod
    async def from_data(cls, data: bytes, volume: float=0.5):
        """
        |coro|

        Asynchronously convert mp3 data to pcm.

        Parameters
        ------------
        data: :class:`bytes`
            MP3 bytes data
        volume: :class:`float`
            Set initial volume for AudioSource, default to `0.5`
        """
        loop = asyncio.get_event_loop()
        c_data = await loop.run_in_executor(None, lambda: cls._decode(data))
        return cls(c_data, volume, converted=True)

    @classmethod
    async def from_file(cls, filename: str, volume: float=0.5):
        """
        |coro|

        Asynchronously convert mp3 data to pcm.

        Parameters
        ------------
        filename: :class:`str`
            MP3 File
        volume: :class:`float`
            Set initial volume for AudioSource, default to `0.5`
        """
        def read_data(cls, filename):
            with open(filename, 'rb') as o:
                data = o.read()
            return cls._decode(data)
        loop = asyncio.get_event_loop()
        c_data = await loop.run_in_executor(None, lambda: read_data(cls, filename))
        return cls(c_data, volume, converted=True)


    def _decode(self, data):
        try:
            miniaudio.mp3_get_info(data)
        except miniaudio.DecodeError:
            raise InvalidMP3('The audio data is not mp3 format') from None

        return miniaudio.decode(data, sample_rate=48000).samples.tobytes()

    def seekable(self):
        return True

class FLACtoPCMAudio(RawPCMAudio):
    """
    Represents flac to PCM audio source.

    This audio source will convert flac to pcm format (16-bit 48KHz).

    Note
    ------
    When you initiate this class, the audio data will automatically coverted to pcm.
    This may cause all asynchronous process is blocked by this process.
    If you want to avoid this, use :class:`FLACtoPCMAudio.from_data` or 
    :class:`FLACtoPCMAudio.from_file`

    Parameters
    ------------
    data: :class:`bytes`
        FLAC bytes data
    volume: :class:`float`
        Set initial volume for AudioSource
    kwargs:
        These parameters will be passed in :class:`RawPCMAudio`

    Attributes
    -----------
    stream: :term:`py:file object`
        A file-like object that reads byte data representing raw PCM.

    Raises
    --------
    InvalidFLAC
        The audio data is not flac format
    """
    def __init__(self, data: bytes, volume: float=0.5, **kwargs):
        converted = kwargs.get('converted')
        if not converted:
            decoded_data = self._decode(data)
        else:
            kwargs.pop('converted')
            decoded_data = data
        super().__init__(io.BytesIO(decoded_data), volume, **kwargs)

    @classmethod
    async def from_data(cls, data: bytes, volume: float=0.5):
        """
        |coro|

        Asynchronously convert flac data to pcm.

        Parameters
        ------------
        data: :class:`bytes`
            FLAC bytes data
        volume: :class:`float`
            Set initial volume for AudioSource, default to `0.5`
        """
        loop = asyncio.get_event_loop()
        c_data = await loop.run_in_executor(None, lambda: cls._decode(data))
        return cls(c_data, volume, converted=True)

    @classmethod
    async def from_file(cls, filename: str, volume: float=0.5):
        """
        |coro|

        Asynchronously convert flac data to pcm.

        Parameters
        ------------
        filename: :class:`str`
            FLAC File
        volume: :class:`float`
            Set initial volume for AudioSource, default to `0.5`
        """
        def read_data(cls, filename):
            with open(filename, 'rb') as o:
                data = o.read()
            return cls._decode(data)
        loop = asyncio.get_event_loop()
        c_data = await loop.run_in_executor(None, lambda: read_data(cls, filename))
        return cls(c_data, volume, converted=True)

    def _decode(self, data):
        try:
            miniaudio.flac_get_info(data)
        except miniaudio.DecodeError:
            raise InvalidFLAC('The audio data is not flac format') from None

        return miniaudio.decode(data, sample_rate=48000).samples.tobytes()

    def seekable(self):
        return True

class VorbistoPCMAudio(RawPCMAudio):
    """
    Represents vorbis to PCM audio source.

    This audio source will convert vorbis to pcm format (16-bit 48KHz).

    Note
    ------
    When you initiate this class, the audio data will automatically coverted to pcm.
    This may cause all asynchronous process is blocked by this process.
    If you want to avoid this, use :class:`VorbistoPCMAudio.from_data` or 
    :class:`VorbistoPCMAudio.from_file`

    Parameters
    ------------
    data: :class:`bytes`
        Vorbis bytes data
    volume: :class:`float`
        Set initial volume for AudioSource
    kwargs:
        These parameters will be passed in :class:`RawPCMAudio`

    Attributes
    -----------
    stream: :term:`py:file object`
        A file-like object that reads byte data representing raw PCM.

    Raises
    --------
    InvalidVorbis
        The audio data is not vorbis codec
    """
    def __init__(self, data: bytes, volume: float=0.5, **kwargs):
        converted = kwargs.get('converted')
        if not converted:
            decoded_data = self._decode(data)
        else:
            kwargs.pop('converted')
            decoded_data = data
        super().__init__(io.BytesIO(decoded_data), volume, **kwargs)

    @classmethod
    async def from_data(cls, data: bytes, volume: float=0.5):
        """
        |coro|

        Asynchronously convert vorbis data to pcm.

        Parameters
        ------------
        data: :class:`bytes`
            Vorbis bytes data
        volume: :class:`float`
            Set initial volume for AudioSource, default to `0.5`
        """
        loop = asyncio.get_event_loop()
        c_data = await loop.run_in_executor(None, lambda: cls._decode(data))
        return cls(c_data, volume, converted=True)

    @classmethod
    async def from_file(cls, filename: str, volume: float=0.5):
        """
        |coro|

        Asynchronously convert vorbis data to pcm.

        Parameters
        ------------
        filename: :class:`str`
            Vorbis File
        volume: :class:`float`
            Set initial volume for AudioSource, default to `0.5`
        """
        def read_data(cls, filename):
            with open(filename, 'rb') as o:
                data = o.read()
            return cls._decode(data)
        loop = asyncio.get_event_loop()
        c_data = await loop.run_in_executor(None, lambda: read_data(cls, filename))
        return cls(c_data, volume, converted=True)

    def _decode(self, data):
        try:
            miniaudio.vorbis_get_info(data)
        except miniaudio.DecodeError:
            raise InvalidVorbis('The audio data is not vorbis codec') from None

        return miniaudio.decode(data, sample_rate=48000).samples.tobytes()

    def seekable(self):
        return True