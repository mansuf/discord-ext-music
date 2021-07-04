class EqualizerError(Exception):
    """
    Raised when something happened in Equalizer class
    """
    pass

class ConverterError(Exception):
    """
    Raised when something happened in Converter class
    """
    pass

class WorkerError(Exception):
    """
    Raised when something happened in Worker class
    """
    pass

class IllegalSeek(Exception):
    """
    Raised when MusicSource trying to seek
    when stream doesn't support seek() operations
    """
    pass

class InvalidMP3(Exception):
    """
    Raised when audio data is not mp3 format
    """
    pass

class InvalidFLAC(Exception):
    """
    Raised when audio data is not flac format
    """
    pass

class InvalidVorbis(Exception):
    """
    Raised when audio data is not vorbis codec
    """
    pass

class MiniaudioError(Exception):
    """
    Raised when something happened in miniaudio module
    """
    pass
