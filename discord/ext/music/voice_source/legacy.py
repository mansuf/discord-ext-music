import sys
import threading
from typing import Union
import discord
import logging
import audioop
import wave
import io

from io import BufferedIOBase
from discord.opus import _OpusStruct as OpusEncoder
from ..utils.errors import EqualizerError, IllegalSeek
from ..equalizer import Equalizer

__all__ = (
    'MusicSource','Silence', 'RawPCMAudio',
    'WAVAudio'
)

log = logging.getLogger(__name__)

class MusicSource(discord.AudioSource):
    """
    same like :class:`discord.AudioSource`, but its have
    seek, rewind, equalizer and volume built-in to AudioSource
    """

    def __init__(self):
        self.__volume__ = None
        self.__equalier__ = None

    def read(self):
        """Reads 20ms worth of audio.

        Subclasses must implement this.

        If the audio is complete, then returning an empty
        :class:`bytes` to signal this is the way to do so.

        If :meth:`is_opus` method returns ``True``, then it must return
        20ms worth of Opus encoded audio. Otherwise, it must be 20ms
        worth of 16-bit 48KHz stereo PCM, which is about 3,840 bytes
        per frame (20ms worth of audio).

        Returns
        --------
        :class:`bytes`
            A bytes like object that represents the PCM or Opus data.
        """
        raise NotImplementedError

    def recreate(self):
        """Recreate audio source, useful for next and previous playback"""
        raise NotImplementedError

    def seekable(self):
        """
        Check if this source support seek() and rewind() operations or not

        return :class:`bool`
        """
        raise False

    def seek(self, seconds: float):
        """Jump forward to specified durations

        Parameters
        -----------
        seconds: :class:`float`
            The duration in seconds that we want to jump forward

        Raises
        -------
        :class:`IllegalSeek`
            current stream doesn't support seek() operations
        """
        raise NotImplementedError()
    
    def rewind(self, seconds: float):
        """Jump back to specified durations

        Parameters
        -----------
        seconds: :class:`float`
            The duration in seconds that we want to jump backward

        Raises
        -------
        :class:`IllegalSeek`
            current stream doesn't support seek() operations
        """
        raise NotImplementedError()

    def get_stream_durations(self):
        """
        Get current stream durations in seconds

        Returns
        --------
        :class:`float`
            The current stream duration in seconds
        """
        raise NotImplementedError()

    @property
    def volume(self):
        """Optional[:class:`float`]: Return current volume"""
        return self.__volume__

    def set_volume(self, volume: Union[float, None]):
        """
        Set volume in float percentage.
        Set to ``None`` to disable volume adjust.

        For example, 0.5 = 50%, 1.5 = 150%

        Parameters
        -----------
        volume: :class:`float`
            Set volume to music source
        """
        self.__volume__ = volume

    @property
    def equalizer(self):
        """Optional[:class:`Equalizer`]: Return current equalizer"""
        return self.__equalier__

    def set_equalizer(self, equalizer: Equalizer=None):
        """
        Set a :class:`Equalizer` to MusicSource.

        Parameters
        -----------
        equalizer: :class:`Equalizer`
            Set equalizer to music source
        """
        self.__equalier__ = equalizer

class Silence(MusicSource):
    def read(self):
        return bytes(bytearray([0xF8, 0xFF, 0xFE]))

    def is_opus(self):
        # Return true so we don't need to encode it
        return True

class RawPCMAudio(MusicSource):
    """Represents raw 16-bit 48KHz stereo PCM audio source.

    Parameters
    ------------
    stream: :class:`io.BufferedIOBase`
        file-like object
    volume: :class:`float` or :class:`NoneType`
        Set initial volume for AudioSource

    Attributes
    -----------
    stream: :class:`io.BufferedIOBase`
        A file-like object that reads byte data representing raw PCM.
    """
    def __init__(
        self,
        stream: BufferedIOBase,
        volume: float=None,
    ):
        super().__init__()
        self.stream = stream
        self._durations = 0
        self._eq = None # type: Equalizer
        self._lock = threading.Lock()
        self._buffered_eq = None
        self.set_volume(volume)

    def read(self):
        with self._lock:
            # Read equalized audio data
            if self.equalizer is not None:
                data = self.equalizer.read()
            else:
                data = self.stream.read(OpusEncoder.FRAME_SIZE)

            if len(data) != OpusEncoder.FRAME_SIZE:
                return b''

            # Change volume audio
            if self.volume is None:
                return data
            else:
                return audioop.mul(data, 2, min(self.volume, 2.0))
    
    def cleanup(self):
        self.stream.close()

    def recreate(self):
        if not self.seekable():
            raise IllegalSeek('current stream doesn\'t support seek() operations')
        with self._lock:
            self.stream.seek(0, 0)

    def seekable(self):
        return self.stream.seekable()

    def get_stream_durations(self):
        return self._durations

    def set_volume(self, volume):
        vol = max(volume, 0.0) if volume is not None else None
        super().set_volume(vol)

    def set_equalizer(self, eq: Equalizer=None):
        if eq is not None:
            if not isinstance(eq, Equalizer):
                raise EqualizerError('{0.__class__.__name__} is not Equalizer'.format(eq))
        with self._lock:
            eq.setup(self.stream)
            super().set_equalizer(eq)

    # -------------------------------------------
    # Formula seek and rewind for PCM-based Audio
    # -------------------------------------------
    #
    # Finding seekable positions IO
    # ---------------------------------------------------------------------------------------------
    # given_seconds * 1000 / 20 (miliseconds) * OpusEncoder.FRAME_SIZE = seekable positions IO
    # ---------------------------------------------------------------------------------------------
    #
    # Formula seek in seconds
    #
    # Find seekable positions IO and then addition it with IO.tell().
    # The complete formula can be see below
    # -----------------------------------------------------------------------------
    # given_seconds * 1000 / 20 (miliseconds) * OpusEncoder.FRAME_SIZE + IO.tell()
    # -----------------------------------------------------------------------------
    # and then use IO.seek() to jump a specified positions
    #
    # Formula rewind in seconds
    #
    # Find seekable positions IO and then subtract it with IO.tell()
    # The complete formula can be see below
    # -----------------------------------------------------------------------------
    # IO.tell() - given_seconds * 1000 / 20 (miliseconds) * OpusEncoder.FRAME_SIZE
    # -----------------------------------------------------------------------------
    # NOTE: IO.tell() subtraction must be placed in front positions otherwise 
    # the result will be negative.
    # and then use IO.seek() to jump a specified positions

    def seek(self, seconds: float):
        if not self.seekable():
            raise IllegalSeek('current stream doesn\'t support seek() operations')

        with self._lock:
            # Current stream positions
            c_pos = self.stream.tell()

            # Seekable stream positions
            s_pos = seconds * 1000 / 20 * OpusEncoder.FRAME_SIZE

            # addition it with c_pos
            s_pos += c_pos

            # convert to integer
            # because seek in IO doesn't support float numbers
            seek = int(s_pos)

            # Make sure seek position aren't negative numbers
            if seek < 0:
                seek = 0

            # Finally jump to specified positions
            self.stream.seek(seek, 0)

            # Change current stream durations
            self._durations = s_pos / 1000 * 20 / OpusEncoder.FRAME_SIZE

    def rewind(self, seconds: float):
        if not self.seekable():
            raise IllegalSeek('current stream doesn\'t support seek() operations')

        with self._lock:
            # Current stream positions
            c_pos = self.stream.tell()

            # Seekable stream positions
            s_pos = seconds * 1000 / 20 * OpusEncoder.FRAME_SIZE

            # subtract it with s_pos
            c_pos -= s_pos

            # convert to integer
            # because seek in IO doesn't support float numbers
            seek = int(c_pos)

            # Make sure seek position aren't negative numbers
            if seek < 0:
                seek = 0

            # Finally jump to specified positions
            self.stream.seek(seek, 0)

            # Change current stream durations
            self._durations = c_pos / 1000 * 20 / OpusEncoder.FRAME_SIZE

class WAVAudio(RawPCMAudio):
    """
    Represents WAV audio stream

    file: Union[:class:`str`, :class:`io.BufferedIOBase`]
        valid file location or file-like object.
    volume: :class:`float` or :class:`NoneType`
        Set initial volume for AudioSource
    kwargs:
        These parameters will be passed in :class:`RawPCMAudio`

    """
    def __init__(self, file: Union[str, io.BufferedIOBase], volume: float=None, **kwargs):
        # Check if this stream is wav format
        if isinstance(file, str):
            stream = open(file, 'rb')
        else:
            stream = file
        new_stream = self._check_wav(stream)
        super().__init__(new_stream, volume, **kwargs)

    def _check_wav_spec(self, wav):
        channels = wav.getnchannels() == 2
        sample_width = wav.getsampwidth() == 2
        frame_rate = wav.getframerate() == 48000
        return channels, sample_width, frame_rate

    def _check_wav(self, stream):
        converted = io.BytesIO()
        info = wave.open(stream, 'rb')

        # If one of wav specifications (16-bit 48KHz) 
        # doesn't meet then convert it
        if False in self._check_wav_spec(info):
            output = wave.open(converted, 'wb')
            output.setnchannels(2)
            output.setsampwidth(2)
            output.setframerate(48000)
        else:
            output = None
            info.close()
            return stream

        # Read the old stream and write it to new stream
        data = stream.read()
        if output:
            output.writeframesraw(data)
            output.close()

        # Close the wave file
        info.close()

        # Jump to 0 pos
        converted.seek(0, 0)
        return converted