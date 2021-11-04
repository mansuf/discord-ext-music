from discord.opus import Encoder as NativeEncoder
from .av import LibAVEncoder, AV_OK

def get_opus_encoder(enc=None):
    # List of available opus encoders
    _opus_encoders = {
        'native': NativeEncoder,
        'av': LibAVEncoder
    }

    if enc:
        try:
            return _opus_encoders[enc]
        except KeyError:
            raise ValueError('invalid opus encoder') from None
    else:
        if AV_OK:
            return _opus_encoders['av']
        else:
            return _opus_encoders['native']

__all__ = (
    'get_opus_encoder', 'NativeEncoder', 'LibAVEncoder'
)