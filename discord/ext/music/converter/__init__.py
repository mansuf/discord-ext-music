import threading
import asyncio
from discord.opus import Encoder
from ..utils.errors import EqualizerError
from ..utils.var import ContextVar

# try to import the equalizer
try:
    from .equalizer import Equalizer
except ImportError:
    EQ_OK = False
else:
    EQ_OK = True

# Set the global converter
_converter = ContextVar()

class Converter:
    class Job:
        def __init__(self, fut, data):
            self.fut = fut
            self.data = data

    def __init__(self, eq: Equalizer=None):
        self._thread = threading.Thread(target=self._worker)
        self._eq = eq
        self.encoder = Encoder()
        self._queue = asyncio.Queue()

        # Queue event
        self._queue_event = threading.Event()

        # Start the thread
        self._thread.start()

    @property
    def eq(self):
        return self._eq
    
    @eq.setter
    def eq(self, value: Equalizer=None):
        self._eq = value

    def _worker(self):
        while True:
            self._queue_event.wait()
            try:
                job = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                continue
            else:
                data = job.data
                if self._eq is not None:
                    converted = self._eq.convert(data)
                else:
                    converted = data
                packet = self.encoder.encode(converted, self.encoder.SAMPLES_PER_FRAME)
                job.fut.put_nowait(packet)
    
    async def convert(self, data):
        self._queue_event.set()
        # The reason why i use asyncio.Queue rather than asyncio.Future
        # because asyncio.Queue support blocking
        fut = asyncio.Queue()
        job = self.Job(fut, data)

        # put in queue
        await self._queue.put(job)

        # wait until data is converted
        return await fut.get()

class _GlobalConverter(Converter):
    # Accept no parameters
    def __init__(self):
        super().__init__()
    
    @property
    def eq(self):
        raise NotImplementedError()

    @eq.setter
    def eq(self, value):
        raise NotImplementedError()

    def _worker(self):
        while True:
            self._queue_event.wait()
            try:
                job = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                continue
            else:
                data = job.data
                packet = self.encoder.encode(data, self.encoder.SAMPLES_PER_FRAME)
                job.fut.put_nowait(packet)

def get_global_converter():
    """
    Get global converter, create one if not exist

    There is difference between global converter and normal converter.
    Global converter doesn't have equalizer, normal converter does.

    """
    if _converter.get() is None:
        _converter.set(_GlobalConverter())
    return _converter.get()
