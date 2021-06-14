import asyncio
import discord

class MusicSource(discord.AudioSource):
    def is_async(self):
        """
        Check if this source is async or not
        return :class:`bool`
        """
        return False


class Silence(MusicSource):
    def read(self):
        return bytearray(8)