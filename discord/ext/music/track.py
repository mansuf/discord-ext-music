from .voice_source import MusicSource

__all__ = ('Track',)

class Track:
    """a class containing MusicSource, name, url, stream url, thumbnail"""
    def __init__(
        self,
        source: MusicSource,
        name: str,
        url: str=None,
        stream_url: str=None,
        thumbnail: str=None
    ) -> None:
        self.name = name
        self.url = url
        self.stream_url = stream_url
        self.source = source
        self.thumbnail = thumbnail

    def __repr__(self) -> str:
        return '<Track name="%s" url="%s">' % (
            self.name,
            self.url
        )