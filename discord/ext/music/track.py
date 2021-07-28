from .voice_source import MusicSource

class Track:
    """a class containing MusicSource, name, url, thumbnail"""
    def __init__(
        self,
        source: MusicSource,
        name: str,
        url: str=None,
        thumbnail: bytes=None
    ) -> None:
        self.name = name
        self.url = url
        self.source = source
        self.thumbnail = thumbnail
