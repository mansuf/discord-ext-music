import math
from pydub import AudioSegment
from pydub.scipy_effects import eq as equalizer
from typing import List, Dict
from .utils.errors import EqualizerError
from .utils.var import ContextVar

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

class Equalizer:
    """
    Equalizer class

    Only PCM codecs support this

    sample_width: :class:`str`
        Set sample width for the equalizer.
        Choices are `8bit`, `16bit`, `32bit`
    channels: :class:`int`
        Set channels for the equalizer.
        Choices are `1` = Mono, and `2` = Stereo.
    frame_rate: :class:`int`
        Set frame_rate for the equalizer.
    freqs: :class:`List[Dict]` (optional, default: `None`)
        a list containing dicts, each dict has frequency (in Hz) and gain (in dB) inside it.
        For example, [{"freq": 20, "gain": 20}, ...]
        You cannot add same frequency in `freqs` argument,
        if you try to add it, it will raise :class:`EqualizerError`.
    """
    def __init__(self, sample_width: str, channels: int, frame_rate: int, freqs: List[Dict]=None):
        if freqs is not None:
            # Check the frequencys
            self._check_freqs(freqs)

            # Parse the equalizers
            self._eqs = self._parse_eqs(freqs)
        else:
            self._eqs = {}

        # Check the sample_width
        try:
            self._sample_width = _SAMPLE_WIDTH[sample_width]
        except KeyError:
            raise EqualizerError('"%s" is not valid sample_width, choices are %s' % (
                sample_width,
                _SAMPLE_WIDTH
            ))

        # Check the channels
        if channels not in _CHANNELS:
            raise EqualizerError('"%s" is not valid channels, choices are %s' % (
                channels,
                _CHANNELS
            ))

        # Check the frame_rate
        if not isinstance(frame_rate, int):
            raise EqualizerError('frame_rate expecting int, got %s' % (type(frame_rate)))

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
    
    def add_frequency(self, freq: int, gain: int):
        """
        Add a frequency, 
        raise :class:`EqualizerError` if given frequency is already exist.
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
        """
        Remove a frequency, 
        raise :class:`EqualizerError` if given frequency is not exist.
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
        raise :class:`EqualizerError` if given frequency is not exist.
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
        """
        Convert audio data to equalized audio data
        """
        _ = AudioSegment(data, metadata=self._eq_args)
        ctx = ContextVar(_)
        for key in self._eqs:
            # Get the equalizer
            eq = self._eqs.get(key)

            # Get the audio segment
            seg = ctx.get()

            # Convert it
            n_seg = equalizer(seg, eq.freq, gain_dB=eq.gain)

            # Set the new converted audio segment
            ctx.set(n_seg)
        return ctx.get().raw_data

class SubwooferEqualizer:
    """
    An easy to use equalizer for bass

    The frequency range is from 20Hz to 60Hz.

    **Only PCM codecs support this**
    
    volume: :class:`float`
        Set volume as float percent.
        For example, 0.5 for 50% and 1.75 for 175%.
    sample_width: :class:`str`
        Set sample width for the equalizer.
        Choices are `8bit`, `16bit`, `32bit`
    channels: :class:`int`
        Set channels for the equalizer.
        Choices are `1` = Mono, and `2` = Stereo.
    frame_rate: :class:`int`
        Set frame_rate for the equalizer.
    """
    def __init__(self, volume: float, sample_width: str, channels: int, frame_rate: int):
        self._freqs = []
        self.volume = volume
        freqs = []
        base_freq = 20
        for _ in range(4):
            freqs.append({
                "freq": base_freq,
                "gain": self.volume
            })
            self._freqs.append(base_freq)
            base_freq += 10
        self.eq = Equalizer(freqs, sample_width, channels, frame_rate)

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, volume):
        # Since given volume 0 or lower will raise error,
        # try to redirectly changed it to lowest dB
        if volume <= 0:
            self._volume = -20

        # Adapted from https://github.com/Rapptz/discord.py/blob/master/discord/opus.py#L392
        self._volume = 20 * math.log10(volume)

    def set_gain(self, dB: float):
        """
        Set frequency gain in dB.
        """
        for freq in self._freqs:
            self.eq.set_gain(freq, dB)
        self._volume = dB

    def convert(self, data):
        """
        Convert audio data to equalized audio data
        """
        return self.eq.convert(data)