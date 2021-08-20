import io
import threading

# https://github.com/mansuf/pyav-django-server/blob/main/pyav/io.py
class LibAVIO(io.RawIOBase):
    """
    IO for PyAV.
    There is few differences between built-in IO and this IO:
    - There is no seek() and tell()
    - using bytearray for storing data
    - once data is readed it will automatically removed
    """
    def __init__(self):
        self.buf = bytearray()
        self.lock = threading.Lock()

    def read(self, n=-1):
        with self.lock:
            if n <= 0:
                data = self.buf[0:]
                del self.buf[0:]
            else:
                data = self.buf[:n]
                del self.buf[:n]
        return bytes(data)

    def write(self, buf):
        with self.lock:
            self.buf += buf
        return len(buf)

    def getvalue(self):
        return self.buf

    def writable(self) -> bool:
        return True