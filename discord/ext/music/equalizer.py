import math
from typing import List, Union
from .utils.errors import EqualizerError
from .utils.var import ContextVar

# Try to import eq function in pydub module
try:
    from pydub import AudioSegment
    from pydub.scipy_effects import eq as equalizer
    EQ_OK = True
except ImportError:
    EQ_OK = False
    

class _EqualizerStruct:
    def __init__(self, freq, gain):
        self.freq = freq
        self.gain = gain

# Valid sample_width from pydub
_SAMPLE_WIDTH = {
    "8bit": 1,
    "16bit": 2,
    "32bit": 4
}

# Valid channels from pydub
_CHANNELS = [1,2]

__all__ = ('Equalizer', 'PCMEqualizer', 'SubwooferPCMEqualizer')

class Equalizer:
    """
    Equalizer class

    This was used for converting original audio data to equalized audio data
    """
    def convert(self, data: bytes):
        """
        Convert audio data

        Subclass must implement this.
        """
        raise NotImplementedError()

class PCMEqualizer(Equalizer):
    """
    A equalizer for Signed-PCM codec

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
        if you try to add it, it will raise :class:`EqualizerError`.
    
    Raises
    -------
    EqualizerError
        pydub and scipy is not installed
    """
    def __init__(self, freqs: List[dict]=None):
        if not EQ_OK:
            raise EqualizerError('pydub and scipy need to be installed in order to use equalizer')

        if freqs is not None:
            # Check the frequencys
            self._check_freqs(freqs)

            # Parse the equalizers
            self._eqs = self._parse_eqs(freqs)
        else:
            self._eqs = {}

        # PCM 16-bit 48000Hz Configurations
        sample_width = _SAMPLE_WIDTH["16bit"]
        channels = 2
        frame_rate = 48000

        # For AudioSegment arguments
        self._eq_args = {
            "sample_width": sample_width,
            "channels": channels,
            "frame_rate": frame_rate,
            "frame_width": channels * sample_width
        }

    def _parse_eqs(self, freqs):
        eqs = {}
        for f in freqs:
            freq = f['freq']
            eqs[freq] = _EqualizerStruct(freq, f['gain'])
        return eqs

    def _check_freqs(self, freqs):
        for freq in freqs:
            # Validate type "freq" in freqs argument
            if not isinstance(freq['freq'], int):
                raise ValueError('freq "%s" in %s is not integer type' % (
                    freq['freq'],
                    freq
                ))
            
            # Validate type "gain" in freqs argument
            elif not isinstance(freq['gain'], float):
                raise ValueError('gain "%s" in %s is not float type' % (
                    freq['gain'],
                    freq
                ))
        unchecked = [i['freq'] for i in freqs]
        checked = []
        for freq in unchecked:
            if freq in checked:
                raise EqualizerError('frequency %s is more than one' % (freq))
            else:
                checked.append(freq)
    
    def _determine_bandwidth(self, freqs):
        if len(freqs) == 1:
            return freqs[0]
        max_freq = max(freqs)
        min_freq = min(freqs)
        return max_freq - min_freq

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
        EqualizerError
            given frequency is already exist
        """
        _ = {"freq": freq, "gain": gain}

        # Is freq and gain type valid ?
        self._check_freqs([_])

        # Check if given frequency is exist
        try:
            eq = self._eqs[freq]
        except KeyError:
            eq = _EqualizerStruct(freq, gain)
            self._eqs.setdefault(freq, eq)
        else:
            raise EqualizerError('frequency %s is more than one, use set_gain() instead' % (
                freq
            ))

    def remove_frequency(self, freq: int):
        """Remove a frequency

        Parameters
        -----------
        freq: :class:`int`
            The frequency that want to add

        Raises
        -------
        EqualizerError
            given frequency is not exist
        """
        _ = {"freq": freq, "gain": 0}

        # Is freq and gain type valid ?
        self._check_freqs([_])

        # Check if given frequency is exist
        try:
            self._eqs.pop(freq)
        except KeyError:
            raise EqualizerError('frequency %s is not exist' % (freq))

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
        EqualizerError
            given frequency is not exist
        """
        _ = {"freq": freq, "gain": gain}

        # Is freq and gain type valid ?
        self._check_freqs([_])

        # Check if given frequency is exist
        eq = self._eqs.get(freq)
        if eq is None:
            raise EqualizerError('frequency %s is not exist' % (freq))
        eq.gain = gain

    def convert(self, data):
        """Convert audio data to equalized audio data

        Parameters
        -----------
        data: :class:`bytes`
            The audio data
        """
        _ = AudioSegment(data, metadata=self._eq_args)
        ctx = ContextVar(_)

        # Determine the bandwidth
        bandwidth = self._determine_bandwidth(list(self._eqs))

        for key in self._eqs:
            # Get the equalizer
            eq = self._eqs.get(key)

            # Get the audio segment
            seg = ctx.get()

            # Convert it
            n_seg = equalizer(seg, eq.freq, bandwidth, gain_dB=eq.gain)

            # Set the new converted audio segment
            ctx.set(n_seg)
        return ctx.get().raw_data

class SubwooferPCMEqualizer(PCMEqualizer):
    """
    An easy to use :class:`PCMEqualizer` for subwoofer

    The base frequency is 60Hz.
    
    Parameters
    -----------
    volume: :class:`float`
        Set initial volume as float percent.
        For example, 0.5 for 50% and 1.75 for 175%.
    """
    def __init__(self, volume: float):
        self.volume = volume
        base_freq = 60
        freqs = [{
            "freq": base_freq,
            "gain": self.volume
        }]
        self._freqs = freqs
        super().__init__(freqs)

    def add_frequency(self, freq: int, gain: Union[int, float]):
        raise NotImplementedError

    def remove_frequency(self, freq: int):
        raise NotImplementedError

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
        self._volume = dB
        super().set_gain(**self._freq)