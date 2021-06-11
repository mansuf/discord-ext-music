from discord.opus import Encoder, Decoder

# try to import the equalizer
try:
    from .equalizer import Equalizer
except ImportError:
    EQ_OK = False
else:
    EQ_OK = True

# Set the global converter
_converter = None

class _GlobalConverter:
    def __init__(self, eq: Equalizer=None):
        self._eq = eq
        self.encoder = Encoder()
    pass

def get_global_converter():
    """
    Get global converter, create one if not exist
    """
    pass

