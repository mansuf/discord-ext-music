import io
import struct

try:
    import av
except ImportError:
    AV_OK = False
else:
    AV_OK = True

class LibAVEncoder:
    """New Opus encoder using PyAV.
    
    This opus encoder has cool features when compared to native encoder, such as:
    - Less CPU usage
    - No `Segmentation Fault` when encoding many audio sources.
    
    """
    SAMPLING_RATE = 48000
    CHANNELS = 2
    FRAME_LENGTH = 20  # in milliseconds
    SAMPLE_SIZE = struct.calcsize('h') * CHANNELS
    SAMPLES_PER_FRAME = int(SAMPLING_RATE / 1000 * FRAME_LENGTH)

    FRAME_SIZE = SAMPLES_PER_FRAME * SAMPLE_SIZE
    _dummy = io.BytesIO()

    def __init__(self, rate=48000) -> None:
        if not AV_OK:
            raise RuntimeError('PyAV is not installed')

        self._opener = av.open(self._dummy, 'w', format='ogg')
        self._stream = self._opener.add_stream('libopus', rate=rate)
        self.sample_rate = rate

    def encode(self, pcm_data, pcm_size):
        # Store encoded opus packets with bytearray
        data = bytearray()

        # Adapted from https://github.com/PyAV-Org/PyAV/blob/main/av/audio/frame.pyx#L129-L131
        # With some modifications
        frame = av.AudioFrame(format='s16', layout='stereo', samples=pcm_size)
        frame.sample_rate = self.sample_rate
        for i, plane in enumerate(frame.planes):
            plane.update(pcm_data[i:])

        # Encode pcm data to opus packets
        packets = self._stream.encode(frame)

        for packet in packets:
            data += packet
        return bytes(data)