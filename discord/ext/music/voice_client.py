import asyncio
import socket
from discord.voice_client import VoiceClient

# This class implement discord.voice_client.VoiceClient
# https://github.com/Rapptz/discord.py/blob/master/discord/voice_client.py#L175
# some functions in this class is not exists, such as:
# _get_voice_packet()
# _encrypt_xsalsa20_poly1305()
# _encrypt_xsalsa20_poly1305_suffix()
# _encrypt_xsalsa20_poly1305_lite()
# send_audio_packet()
# checked_add()
# Because they will be moved to discord.ext.music.player.MusicPlayer
class MusicClient(VoiceClient):
    def __init__(self, client, channel):
        super().__init__(client, channel)
        # Deleted functions
        DELETED_FUNCTIONS = [
            '_get_voice_packet',
            '_encrypt_xsalsa20_poly1305',
            '_encrypt_xsalsa20_poly1305_suffix',
            '_encrypt_xsalsa20_poly1305_lite',
            'send_audio_packet',
            'checked_add'
        ]

        # Deleted attributes
        DELETED_ATTRIBUTES = [
            'sequence',
            'timestamp',
            'encoder',
            '_lite_once'
        ]

        # Delete it now
        for func in DELETED_FUNCTIONS:
            delattr(self, func)
        for attr in DELETED_ATTRIBUTES:
            delattr(self, attr)
        
        # For MusicPlayer
        self._connected = asyncio.Event()

    async def connect(self, *, reconnect: bool, timeout: bool):
        await super().connect(reconnect, timeout)
        self._voice_conn = await asyncio.open_connection(
            self.endpoint_ip,
            self.voice_port,
            ssl=True,
            sock=self.socket
        )