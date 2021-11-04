import io

__all__ = ('Equalizer',)

class Equalizer:
    """Represent a equalizer for converting audio.

    Sub-classes must implement this.
    """
    def __init__(self):
        self.__stream__ = None # type: io.BufferedIOBase

    @property
    def stream(self) -> io.BufferedIOBase:
        """:class:`io.BufferedIOBase`: Return the audio stream"""
        if self.__stream__ is None:
            raise RuntimeError('setup() is not called')
        return self.__stream__

    def setup(self, stream):
        """Initialize audio stream to Equalizer
        
        Warning
        --------    
        This is important to call it first, before equalizing audio.
        
        Parameters
        -----------
        stream: :class:`io.BufferedIOBase`
            The audio stream that we want to equalize.
        """
        self.__stream__ = stream

    def read(self):
        """Read audio stream and return equalized audio data."""
        raise NotImplementedError

    def close(self):
        """Close audio stream and do some cleanup to the equalizer."""
        raise NotImplementedError