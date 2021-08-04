from discord.player import AudioSource
from .stream import LibAVStream
from ..legacy import RawPCMAudio, Silence


class LibAVPCMAudio(RawPCMAudio):
    def __init__(self, url_or_file: str, volume: float=0.5) -> None:
        self.kwargs = {
            "url": url_or_file,
            "format": 's16le',
            "codec": 'pcm_s16le',
            "rate": 48000
        }
        stream = LibAVStream(
        )
        super().__init__(stream, volume)

    def seekable(self):
        return True
    
    def seek(self, seconds: float):
        with self._lock:
            pos = self.stream.pos
            self.stream = Silence()
            kwargs = self.kwargs.copy()
            kwargs['seek'] = pos + seconds
            new_stream = LibAVStream(**kwargs)
            self.stream = new_stream
        pass

    def rewind(self, seconds: float):
        pass

