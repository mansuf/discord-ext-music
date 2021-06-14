import threading
import asyncio
from .utils.errors import WorkerError
from .utils.var import ContextVar

# Set global worker
_worker = ContextVar()

class _Worker(threading.Thread):
    class Job:
        def __init__(self, fut, queue, func):
            self.fut = fut
            self.func = func
            self.queue = queue

    def __init__(self):
        self.queue = asyncio.Queue(100)
        self.event = threading.Event()
    
    def is_full(self):
        return self.queue.full()

    def run(self):
        while True:
            self.event.wait()
            try:
                job = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                continue
            else:
                fut = job.fut
                func = job.func
                try:
                    result = func()
                except Exception as e:
                    fut.set_exception(e)
                else:
                    fut.set_result(result)
                job.queue.put_nowait(fut)

    async def submit(self, func):
        self.event.set()
        queue = asyncio.Queue()
        fut = asyncio.Future()
        job = self.Job(fut, queue, func)

        # put in queue
        await self.queue.put(job)

        # wait until func is finished
        await queue.get()

        # Retrieve the exception
        exception = fut.exception()

        # Raise exception if func is error
        # during executions
        if exception is not None:
            raise exception
        
        # Return the result
        return fut.result()

class Worker:
    def __init__(self, max_worker=None):
        if max_worker is not None and not isinstance(max_worker, int):
            raise ValueError("max_worker expecting NoneType or int, got %s" % (
                type(max_worker)
            ))
        self._max_worker = max_worker
        self._current_workers = 0
        self._workers = []

    def _get_worker(self):
        if self._current_workers == 0:
            return self._add_worker()
        for worker in self._workers:
            if not worker.is_full():
                return worker
            else:
                return self._add_worker()

    def _add_worker(self):
        if self._max_worker is not None:
            if self._current_workers + 1 > self._max_worker:
                raise WorkerError('Worker is full')
        t = _Worker()
        t.start()
        self._workers.append(t)
        self._current_workers += 1
        return t

    async def submit(self, func: lambda: callable):
        """
        submit a job

        func: :class:`lambda` or `callable`
            a callable function or lambda
        """
        worker = self._get_worker()
        return await worker.submit(func)

def get_global_worker() -> Worker:
    """
    Return global worker, create one if not exist.

    This worker doesn't have limit,
    if you want to set limit use :class:`Worker` class instead.

    This should be used for :class:`MusicClient` or :class:`MusicPlayer` only
    """
    if _worker.get() is None:
        _worker.set(Worker())
    return _worker.get()