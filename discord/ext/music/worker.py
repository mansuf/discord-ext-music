import threading
import asyncio
import queue
from concurrent.futures import Future
from .utils.errors import WorkerError
from .utils.var import ContextVar

class QueueWorker(threading.Thread):
    """
    A Queue worker used for asynchronous computation
    """
    class Job:
        def __init__(self, fut, func):
            self.fut = fut
            self.func = func

    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.queue = queue.Queue()
        self.start()
    
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
            else:
                fut.set_result(result)

    async def submit(self, func):
        """
        |coro|

        submit a job and wait until it finished

        Parameters
        -----------
        func: :class:`lambda` or `callable`
            a callable function or lambda
        """
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
