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