import math
import io

from typing import List, Union
from discord.opus import _OpusStruct as OpusStruct
from .base import Equalizer

# Try to import eq function in pydub module
try:
    from pydub import AudioSegment
    from pydub.scipy_effects import eq as equalizer
    EQ_OK = True
except ImportError:
    EQ_OK = False

__all__ = (
    'pydubError', 'pydubEqualizer', 'pydubSubwooferEqualizer'
)

class pydubError(Exception):
    pass

class pydubEqualizer(Equalizer):
    """A pydub equalizer for Signed-PCM codec

    The audio specifications must be 16-bit 48KHz

    Warning
    --------
    You must have `scipy`_ and `pydub`_ installed, otherwise you will get error.

    .. _scipy: https://pypi.org/project/scipy/
    .. _pydub: https://pypi.org/project/pydub/

    Parameters
    -----------
    freqs: Optional[List[:class:`dict`]]
        a list containing dict, each dict has frequency (in Hz) and gain (in dB) inside it.
        For example, [{"freq": 20, "gain": 20}, ...]
        You cannot add same frequencys,
        if you try to add it, it will raise :class:`pydubError`.
    
    Raises
    -------
    pydubError
        pydub and scipy is not installed
    """

    def __init__(self, freqs: List[dict]=None):
        if not EQ_OK:
            raise pydubError('pydub and scipy need to be installed in order to use pydubEqualizer')

        self._buffered = None

        if freqs is not None:
            # Parse the frequencys
            self._freqs = self._parse_freqs(freqs)
        else:
            self._freqs = {}

        # PCM 16-bit 48000Hz Configurations
        sample_width = 2
        channels = 2
        frame_rate = 48000

        # For AudioSegment arguments
        self._eq_args = {
            "sample_width": sample_width,
            "channels": channels,
            "frame_rate": frame_rate,
            "frame_width": channels * sample_width
        }

    def _determine_bandwidth(self, freqs):
        if len(freqs) == 1:
            return freqs[0]
        max_freq = max(freqs)
        min_freq = min(freqs)
        return max_freq - min_freq

    def _parse_freqs(self, freqs):
        duplicate = []
        new_freqs = {} # key: freq, value: gain
        for data in freqs:
            freq = data.get('freq')
            gain = data.get('gain')

            if not freq:
                raise ValueError('missing "freq" key in %s' % data)
            
            if not gain:
                raise ValueError('missing "gain" key in %s' % data)
            
            self._check_freq(freq, gain)

            if freq not in duplicate:
                duplicate.append(freq)
            else:
                raise ValueError('frequency "%s" is more than one')

            new_freqs[freq] = gain
        return new_freqs

    def _check_freq(self, freq=None, gain=None):
        if freq and not isinstance(freq, int):
            raise ValueError('freq "%s" is not integer type' % freq)
        
        if gain:
            if isinstance(gain, int) or isinstance(gain, float):
                pass
            else:
                raise ValueError('gain "%s" is not integer or float type' % gain)

    def add_frequency(self, freq: int, gain: Union[int, float]):
        """Add a frequency

        Parameters
        -----------
        freq: :class:`int`
            The frequency that want to add
        gain: Union[:class:`int`, :class:`float`]
            The gain frequency

        Raises
        -------
        ValueError
            given frequency is already exist
        """
        self._check_freq(freq, gain)

        try:
            self._freqs[freq]
        except KeyError:
            self._freqs.setdefault(freq, gain)
        else:
            raise ValueError('frequency "%s" is more than one, use set_gain() instead' % freq)

    def remove_frequency(self, freq: int):
        """Remove a frequency

        Parameters
        -----------
        freq: :class:`int`
            The frequency that want to add

        Raises
        -------
        ValueError
            given frequency is not exist
        """
        self._check_freq(freq)

        try:
            self._freqs.pop(freq)
        except KeyError:
            raise ValueError('frequency %s is not exist' % freq)
    
    def set_gain(self, freq: int, gain: int):
        """
        Set frequency gain in dB,

        Parameters
        -----------
        freq: :class:`int`
            The frequency want to increase the gain
        gain: Union[:class:`int`, :class:`float`]
            The value want to increase or lower

        Raises
        -------
        ValueError
            given frequency is not exist
        """
        self._check_freq(freq, gain)

        if self._freqs.get(freq) is None:
            raise ValueError('frequency %s is not exist' % freq)
        self._freqs[freq] = gain

    def _read_buffered_data(self):
        # Read the buffered data
        data = self._buffered.read(OpusStruct.FRAME_SIZE)
        
        if not data:
            # For re-use
            self._buffered = None
            return None
        elif len(data) != OpusStruct.FRAME_SIZE:
            # For re-use
            self._buffered = None

            return b''
        else:
            return data

    def read(self):
        while True:
            if self._buffered is None:
                # The equalizer cannot convert audio if duration is too small (ex: 20ms)
                # they will reproduce noisy sound.
                # So the pydubEqualizer must read audio data for at least 1 second
                # and then equalize it and move it to buffered equalized audio data.

                data = self.stream.read(50 * OpusStruct.FRAME_SIZE)

                if not data:
                    return b''

                # 1 second duration
                _ = AudioSegment(data, metadata=self._eq_args)
                segment = None

                # Determine the bandwidth
                bandwidth = self._determine_bandwidth(list(self._freqs))

                # Equalize the audio
                for frequency, gain in self._freqs.items():
                    try:
                        if segment is None:
                            segment = equalizer(_, frequency, bandwidth, gain_dB=gain)
                        else:
                            segment = equalizer(segment, frequency, bandwidth, gain_dB=gain)
                    except Exception:
                        raise pydubError('equalizing audio data failed')
                
                # Make buffered data
                self._buffered = io.BytesIO(segment.raw_data)

                final_data = self._read_buffered_data()
            else:
                final_data = self._read_buffered_data()
                if final_data is None:
                    continue
            
            return final_data
            

class pydubSubwooferEqualizer(Equalizer):
    """
    An easy to use :class:`pydubEqualizer` for subwoofer

    The frequency is 60Hz.
    
    Parameters
    -----------
    volume: :class:`float`
        Set initial volume as float percent.
        For example, 0.5 for 50% and 1.75 for 175%.
    """
    def __init__(self, volume: float=0.5):
        self._freq = 60
        freqs = [{
            "freq": self._freq,
            "gain": 1 # initialization
        }]
        self._eq = pydubEqualizer(freqs)
        self.volume = volume

    @property
    def volume(self) -> float:
        """Optional[:class:`float`]: The subwoofer volume in float numbers
        
        This property can also be used to change the subwoofer volume.
        """
        return self._volume

    @volume.setter
    def volume(self, volume):
        # Since given volume 0 or lower will raise error,
        # try to redirectly changed it to lowest dB
        if volume <= 0:
            self._volume = -20.0
            self.set_gain(self._volume)
            return

        # Adapted from https://github.com/Rapptz/discord.py/blob/master/discord/opus.py#L392
        self._volume = 20 * math.log10(volume)
        self.set_gain(self._volume)

    def set_gain(self, dB: float):
        """
        Set frequency gain in dB.
        """
        self._eq.set_gain(self._freq, dB)

    def setup(self, stream):
        self._eq.setup(stream)

    def read(self):
        return self._eq.read()