
__all__ = ('Equalizer',)

class Equalizer:
    """Represent a equalizer for converting audio.

    Sub-classes must implement this.

    Parameters
    ------------
    stream: BufferedIOBase
        Audio stream
    """
    def __init__(self, stream):
        pass

    def read(self):
        """Read audio stream and return equalized audio data."""
        raise NotImplementedError
    
    def seek(self, offset, whence):
        """Seek directly to the audio stream."""
        raise NotImplementedError

    def close(self):
        """Close audio stream and do some cleanup to the equalizer."""
        raise NotImplementedError