import asyncio
import discord
import logging
import sys
import nacl.secret
import struct
import time
import traceback
from discord import opus
from .voice_client import MusicClient
from .voice_source import MusicSource, Silence
from .worker import QueueWorker

log = logging.getLogger(__name__)
