from .stream import LibAVStream
from discord.oggparse import OggStream
from discord.player import AudioSource


class LibAVOpusAudio(AudioSource):
    def __init__(self, url_or_file: str) -> None:
        self.url = url_or_file
        self.stream = LibAVStream(
            url_or_file,
            'ogg',
            'libopus',
            48000
        )
        self.ogg_stream = OggStream(self.stream).iter_packets()
    
    def read(self):
        return next(self.ogg_stream, b'')
        # return data

    def seek(self, seconds: float):
        self.stream.seek(self.stream.pos + seconds)
    
    def rewind(self, seconds: float):
        self.stream.seek(self.stream.pos - seconds)

    def cleanup(self):
        return self.stream.close()

    def is_opus(self):
        return True