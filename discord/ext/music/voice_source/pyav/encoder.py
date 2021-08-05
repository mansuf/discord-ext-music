"""
IMPORTANT NOTE: DO NOT USE THIS!!!!
This codes below will be used for next development
such as volume control in LibAVStream, etc
"""

import av
import io
from .io import LibAVIO

PCM_SIZE = 3840

class OpusEncoder:
    FRAME_SIZE = PCM_SIZE

    def __init__(self, rate=48000) -> None:
        self._buffer_encoder = LibAVIO()
        self._encoder = av.open(self._buffer_encoder, 'w', format='ogg')
        self._encoder_stream = self._encoder.add_stream('libopus', rate=rate)
        self._decoder = av.open(io.BytesIO(), 'r', format='s16le')
        audio_stream = self._decoder.streams.get(audio=0)[0]
        audio_stream.codec_context.sample_rate = 48000
        audio_stream.codec_context.channels = 2
        print(audio_stream)
        self._decoder = audio_stream


    def encode(self, pcm_packets):
        data = bytearray()
        for packet in pcm_packets:
            frames = self._decoder.decode(packet)
            # print(frames)
            for frame in frames:
                new_packets = self._encoder_stream.encode(frame)
                # print(new_packets)
                for packet in new_packets:
                    if packet.is_corrupt:
                        print('FOUND CORRUPTED', packet)
                        exit(0)
                self._encoder.mux(new_packets)
                # for packet in new_packets:
                #     # print(packet.to_bytes())
                #     data += bytes(packet)
        return self._buffer_encoder.read()
        # print(len(self._buffer_encoder.buf))
        # return self._buffer_encoder.read()
        # return b''
