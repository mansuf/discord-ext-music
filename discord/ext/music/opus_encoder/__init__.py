from discord.opus import Encoder as NativeEncoder
from .av import LibAVEncoder

__all__ = (
    'NativeEncoder', 'LibAVEncoder'
)