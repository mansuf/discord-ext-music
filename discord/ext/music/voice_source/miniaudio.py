import asyncio
import io
from .legacy import RawPCMAudio, MusicSource
from ..worker import QueueWorker
from ..utils.errors import InvalidMP3, MiniaudioError

# Try to import miniaudio module
try:
    import miniaudio
except ImportError:
    raise MiniaudioError('miniaudio isn\'t installed') from None

class MP3Audio(MusicSource):
    """
    Represents mp3 audio stream.

    This audio stream will produce PCM packets (16-bit 48KHz).

    Parameters
    ------------
    data: :class:`bytes`
        MP3 bytes data
    volume: :class:`float`
        Set initial volume for :classs:`MP3Audio`


    """

class MP3toPCMAudio(RawPCMAudio):
    """
    Represents mp3 to PCM audio source.

    This audio source will convert mp3 to pcm format (16-bit 48KHz).

    Note
    ------
    When you initiate this class, the audio data will automatically coverted to pcm.
    This may cause all asynchronous process is blocked by this process.
    If you want to avoid this, use :class:`MP3toPCMAudio.from_data` or 
    :class:`MP3toPCMAudio.from_file`

    Parameters
    ------------
    data: :class:`bytes`
        MP3 bytes data
    volume: :class:`float`
        Set initial volume for AudioSource

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
    async def from_data(cls, data: bytes, volume: float=0.5, worker: QueueWorker=None):
        """
        |coro|

        Asynchronously convert mp3 data to pcm.

        Parameters
        ------------
        data: :class:`bytes`
            MP3 bytes data
        volume: :class:`float` (default: `0.5`)
            Set initial volume for AudioSource
        worker: :class:`QueueWorker` (default: `None`)
            Set a :class:`QueueWorker` to convert the audio data
        """
        loop = asyncio.get_event_loop()
        if worker is not None:
            c_data = await worker.submit(lambda: cls._decode(data))
        else:
            c_data = await loop.run_in_executor(None, lambda: cls._decode(data))
        mp3 = cls(c_data, volume, converted=True)
        return mp3

    @classmethod
    async def from_file(cls, filename: str, volume: float=0.5, worker: QueueWorker=None):
        """
        |coro|

        Asynchronously convert mp3 data to pcm.

        Parameters
        ------------
        filename: :class:`str`
            MP3 File
        volume: :class:`float` (default: `0.5`)
            Set initial volume for AudioSource
        worker: :class:`QueueWorker` (default: `None`)
            Set a :class:`QueueWorker` to convert the audio data
        """
        with open(filename, 'rb') as o:
            data = o.read()
        loop = asyncio.get_event_loop()
        if worker is not None:
            c_data = await worker.submit(lambda: cls._decode(data))
        else:
            c_data = await loop.run_in_executor(None, lambda: cls._decode(data))
        mp3 = cls(c_data, volume, converted=True)
        return mp3


    def _decode(self, data):
        try:
            miniaudio.mp3_get_info(data)
        except miniaudio.DecodeError:
            raise InvalidMP3('The audio data is not mp3 format') from None

        return miniaudio.decode(data, sample_rate=48000).samples.tobytes()

    def seekable(self):
        return True