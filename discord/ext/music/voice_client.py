import asyncio
import socket
import threading
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
        
        # This will be used if bot is leaving voice channel
        self._leaving = threading.Event()

    async def on_voice_state_update(self, data):
        self.session_id = data['session_id']
        channel_id = data['channel_id']

        if not self._handshaking or self._potentially_reconnecting:
            # If we're done handshaking then we just need to update ourselves
            # If we're potentially reconnecting due to a 4014, then we need to differentiate
            # a channel move and an actual force disconnect
            if channel_id is None:
                # We're being disconnected so cleanup
                self._leaving.set()
                await self.disconnect()
            else:
                guild = self.guild
                self.channel = channel_id and guild and guild.get_channel(int(channel_id))
        else:
            self._voice_state_complete.set()

    async def on_voice_server_update(self, data):
        print('vs', data)
        return await super().on_voice_server_update(data)

    async def connect(self, *, reconnect: bool, timeout: bool):
        await super().connect(reconnect=reconnect, timeout=timeout)