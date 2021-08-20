from discord.errors import DiscordException

class EqualizerError(DiscordException):
    """
    Raised when something happened in Equalizer class
    """
    pass

class IllegalSeek(DiscordException):
    """
    Raised when MusicSource trying to seek
    when stream doesn't support seek() operations
    """
    pass

class InvalidMP3(DiscordException):
    """
    Raised when audio data is not mp3 format
    """
    pass

class InvalidFLAC(DiscordException):
    """
    Raised when audio data is not flac format
    """
    pass

class InvalidVorbis(DiscordException):
    """
    Raised when audio data is not vorbis codec
    """
    pass

class InvalidWAV(DiscordException):
    """
    Raised when audio data is not WAV format
    """


class MiniaudioError(DiscordException):
    """
    Raised when something happened in miniaudio module
    """
    pass

class LibAVError(DiscordException):
    """
    Raised when something happened in LibAV stream
    """
    pass

class TrackNotExist(DiscordException):
    """
    Raised when track is trying to be removed while it not exist
    """
    pass

class MusicClientException(DiscordException):
    """Base exception for MusicClient class"""
    pass

class MusicNotPlaying(MusicClientException):
    """Music is not playing"""
    pass

class MusicAlreadyPlaying(MusicClientException):
    """Music is already playing"""
    pass

class NoMoreSongs(MusicClientException):
    """No more songs in playlist"""
    pass

class NotConnected(MusicClientException):
    """Not connected to voice"""
    pass