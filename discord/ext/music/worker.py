import threading
import asyncio
import queue
from concurrent.futures import Future
from .utils.errors import WorkerError
from .utils.var import ContextVar

# Set music worker
_music_worker = ContextVar()

class _Worker(threading.Thread):
    class Job:
        def __init__(self, fut,func):
            self.fut = fut
            self.func = func

    def __init__(self, limit_job: int=None):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.queue = queue.Queue(limit_job or 0)
    
    def is_full(self):
        return self.queue.full()

    def run(self):
        while True:
            job = self.queue.get()
            fut = job.fut
            func = job.func
            try:
                result = func()
            except Exception as e:
                fut.set_exception(e)
            async def complete():
                fut.set_result(result)
            if isinstance(fut, asyncio.Future):
                asyncio.run_coroutine_threadsafe(complete(), fut.get_loop())


    async def submit(self, func):
        fut = asyncio.Future()
        job = self.Job(fut, func)

        # put in queue
        self.queue.put_nowait(job)

        # wait until func is finished
        await fut

        # Retrieve the exception
        exception = fut.exception()

        # Raise exception if func is error
        # during execution
        if exception is not None:
            raise exception
        
        # Return the result
        return fut.result()

    def submit_nowait(self, func):
        fut = Future()
        job = self.Job(fut, func)

        # put in queue
        self.queue.put_nowait(job)

        return fut

class QueueWorker:
    """
    A Queue worker used for asynchronous computation

    Parameters
    ------------
    max_worker: :class:`int` (Optional, default: `None`)
        Set maximum worker for QueueWorker
        if worker reached its limit, it will raise :class:`WorkerError`
    max_limit_job: :class:`int` (Optional, default: `None`)
        Set maximum limit job for each worker
    """
    def __init__(self, max_worker: int=None, max_limit_job: int=None):
        if max_worker is not None and not isinstance(max_worker, int):
            raise ValueError("max_worker expecting NoneType or int, got %s" % (
                type(max_worker)
            ))
        if max_limit_job is not None and not isinstance(max_limit_job, int):
            raise ValueError("max_limit_job expecting NoneType or int, got %s" % (
                type(max_limit_job)
            ))
        self._max_worker = max_worker
        self._max_limit_job = max_limit_job
        self._current_workers = 0
        self._workers = []
        self._lock = threading.Lock()

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
        t = _Worker(self._max_limit_job)
        t.start()
        self._workers.append(t)
        self._current_workers += 1
        return t

    async def submit(self, func: lambda: callable):
        """
        |coro|

        submit a job and wait until it finished

        Parameters
        -----------
        func: :class:`lambda` or `callable`
            a callable function or lambda
        """
        with self._lock:
            worker = self._get_worker()
        return await worker.submit(func)

    def submit_nowait(self, func: lambda: callable):
        """
        submit a job without waiting until finished

        Parameters
        -----------
        func: :class:`lambda` or `callable`
            a callable function or lambda

        Return :class:`concurrent.futures.Future`
        """
        with self._lock:
            worker = self._get_worker()
        return worker.submit_nowait(func)

def get_music_worker() -> QueueWorker:
    """
    Return music worker, create one if not exist.

    This worker doesn't have limit,
    if you want to set limit use :class:`Worker` class instead.

    This should be used for :class:`MusicClient` or :class:`MusicPlayer` only
    """
    if _music_worker.get() is None:
        _music_worker.set(QueueWorker(max_limit_job=10))
    return _music_worker.get()