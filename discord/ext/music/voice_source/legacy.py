import sys
import threading
import discord
import logging
import audioop
import wave
import io
from io import IOBase
from discord.opus import _OpusStruct as OpusEncoder
from ..utils.errors import EqualizerError, IllegalSeek

# Try to import equalizer module
try:
    from ..equalizer import PCMEqualizer, Equalizer
    EQ_OK = True
except EqualizerError:
    # If failed to import equalizer module
    # Re-create Equalizer class with no methods
    class Equalizer:
        def convert(self):
            raise NotImplementedError
    class PCMEqualizer(Equalizer):
        pass
    EQ_OK = False

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

    def set_volume(self, volume: float):
        """
        Set volume in float percentage

        For example, 0.5 = 50%, 1.5 = 150%

        Parameters
        -----------
        volume: :class:`volume`
            Set volume to music source
        """
        raise NotImplementedError()

    def set_equalizer(self, equalizer: Equalizer=None):
        """
        Set a :class:`Equalizer` to MusicSource.

        Parameters
        -----------
        equalizer: :class:`Equalizer`
            Set equalizer to music source
        """
        raise NotImplementedError()

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
    volume: :class:`float` or :class:`NoneType` (Optional, default: `0.5`)
        Set initial volume for AudioSource

    Attributes
    -----------
    stream: :term:`py:file object`
        A file-like object that reads byte data representing raw PCM.
    """
    def __init__(
        self,
        stream: IOBase,
        volume: float=0.5,
    ):
        self.stream = stream
        self._durations = 0
        self._eq = None
        self._lock = threading.Lock()
        self._buffered_eq = None
        self._volume = max(volume, 0.0)

    def read(self):
        while True:
            if self._eq is not None:
                # At this point if RawPCMAudio using PCMEqualizer,
                # the equalizer cannot convert audio if duration is too small (ex: 20ms)
                # they will reproduce noisy sound.
                # So the RawPCMAudio must read audio data at least for 1 second
                # and then equalize it and move it to buffered equalized audio data.

                def equalize(self, result=False):
                    # The source will read the stream at least 1 second duration
                    data = self.stream.read(OpusEncoder.FRAME_SIZE * 50) # 1 second duration

                    # Return "exhausted" bytes to prevent re-reading stream
                    if not data:
                        return io.BytesIO(b'exhausted')

                    # And then convert / equalize it
                    eq_data = self._eq.convert(data)

                    # Store it in buffered equalized audio data
                    buffered_eq = io.BytesIO(eq_data)

                    if result:
                        return buffered_eq

                if self._buffered_eq is None:
                    self._buffered_eq = equalize(self, True)

                # Read the buffered equalized audio data
                data = self._buffered_eq.read(OpusEncoder.FRAME_SIZE)

                if not data:
                    self._buffered_eq = None
                    continue
                elif len(data) != OpusEncoder.FRAME_SIZE:
                    return b''
                self._durations += 0.020 # 20ms
                if self._volume is None:
                    return data
                else:
                    return audioop.mul(data, 2, min(self._volume, 2.0))
            else:
                if self._buffered_eq is not None:
                    # Make sure that buffered eq is exhausted
                    data = self._buffered_eq.read(OpusEncoder.FRAME_SIZE)
                    if not data:
                        self._buffered_eq = None
                        continue
                else:
                    data = self.stream.read(OpusEncoder.FRAME_SIZE)
                if len(data) != OpusEncoder.FRAME_SIZE:
                    return b''
                self._durations += 0.020 # 20ms
                if self._volume is None:
                    return data
                else:
                    return audioop.mul(data, 2, min(self._volume, 2.0))
    
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

    def set_volume(self, volume: float):
        self._volume = max(volume, 0.0)

    def set_equalizer(self, eq: PCMEqualizer=None):
        if not EQ_OK:
            raise EqualizerError('pydub and scipy need to be installed in order to use equalizer')
        if eq is not None:
            if not isinstance(eq, PCMEqualizer):
                raise EqualizerError('{0.__class__.__name__} is not PCMEqualizer'.format(eq))
        self._eq = eq

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

    stream: :class:`io.BufferedIOBase`
        file-like object
    volume: :class:`float` or :class:`NoneType` (Optional, default: `0.5`)
        Set initial volume for AudioSource
    kwargs:
        These parameters will be passed in :class:`RawPCMAudio`

    """
    def __init__(self, stream: io.IOBase, volume: float=0.5, **kwargs):
        # Check if this stream is wav format
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
        output = wave.open(converted, 'wb')

        # If one of wav specifications (16-bit 48KHz) 
        # doesn't meet then convert it
        if False in self._check_wav_spec(info):
            output.setnchannels(2)
            output.setsampwidth(2)
            output.setframerate(48000)
        else:
            output.close()
            info.close()
            return stream

        # Read the old stream and write it to new stream
        data = stream.read()
        output.writeframesraw(data)

        # Close the wave file
        info.close()
        output.close()

        # Jump to 0 pos
        converted.seek(0, 0)
        return converted