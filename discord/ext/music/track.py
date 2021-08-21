from .voice_source import MusicSource

__all__ = ('Track',)

class Track:
    """A audio track containing audio source, name, url, stream_url, thumbnail
    
    Parameters
    -----------
    source: :class:`MusicSource`
        The audio source of this track
    name: :class:`str`
        Name of this track
    url: :class:`str`
        Webpage url of this track
    stream_url: :class:`str`
        Streamable url of this track
    thumbnail: :class:`str`
        Valid thumbnail url of this track
    
    Attributes
    -----------
    source: :class:`MusicSource`
        The audio source of this track
    name: :class:`str`
        Name of this track
    url: :class:`str`
        Webpage url of this track
    stream_url: :class:`str`
        Streamable url of this track
    thumbnail: :class:`str`
        Valid thumbnail url of this track
    """
    def __init__(
        self,
        source: MusicSource,
        name: str,
        url: str=None,
        stream_url: str=None,
        thumbnail: str=None,
        **kwargs
    ) -> None:
        self.name = name
        self.url = url
        self.stream_url = stream_url
        self.source = source
        self.thumbnail = thumbnail

        # Set up atttributes from kwargs
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def __repr__(self) -> str:
        return '<Track name="%s" url="%s">' % (
            self.name,
            self.url
        )