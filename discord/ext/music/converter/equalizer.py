from pydub import AudioSegment
from pydub.scipy_effects import eq as equalizer
from typing import List, Dict
from ..utils.errors import EqualizerError
from ..utils.var import ContextVar

class _Frequency:
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

    freqs: :class:`List[Dict]`
        a list containing dicts, each dict has frequency (in Hz) and gain (in dB) inside it.
        For example, [{"freq": 20, "gain": 20}, ...]
        You cannot add same frequency in `freqs` argument,
        if you try to add it, it will raise :class:`EqualizerError`.
    sample_width: :class:`str`
        Set sample width for the equalizer.
        Choices are `8bit`, `16bit`, `32bit`
    channels: :class:`int`
        Set channels for the equalizer.
        Choices are `1` = Mono, and `2` = Stereo.
    frame_rate: :class:`int`
        Set frame_rate for the equalizer.
    """
    def __init__(self, freqs: List[Dict], sample_width: str, channels: int, frame_rate: int):
        # Check the frequencys
        self._check_freqs(freqs)

        # Parse the equalizers
        self._eqs = self._parse_eqs(freqs)

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
        eqs = []
        for f in freqs:
            eqs.append(_Frequency(f['freq'], f['gain']))
        return eqs

    def _check_freqs(self, freqs):
        unchecked = [i['freq'] for i in freqs]
        checked = []
        for freq in unchecked:
            if freq in checked:
                raise EqualizerError('frequency %s is more than one')
            else:
                checked.append(freq)
    
    def add_frequency(self, freq: int, gain: int):
        pass

    def convert(self, data):
        """
        Convert audio data to equalized audio data
        """
        _ = AudioSegment(data, metadata=self._eq_args)
        ctx = ContextVar(_)
        for eq in self._eqs:
            seg = ctx.get()
            n_seg = equalizer(seg, eq.freq, gain_dB=eq.gain)
            ctx.set(n_seg)
        return ctx.get().raw_data
