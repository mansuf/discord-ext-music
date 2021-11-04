from discord.opus import Encoder as NativeOpusEncoder
from .av import LibAVOpusEncoder

__all__ = (
    'NativeOpusEncoder', 'LibAVOpusEncoder'
)