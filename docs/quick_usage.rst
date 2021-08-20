Quick Usage
============

.. code-block:: python3

    from discord.ext.commands import Bot
    from discord.ext.music import MusicClient, WavAudio, Track

    bot = Bot()

    @client.command()
    async def play(ctx):
        voice_user = ctx.message.author.voice
        music_client = await voice_user.channel.connect(cls=MusicClient)
        track = Track(
            WavAudio('audio.wav'), # AudioSource
            'This is audio' # name
        )
        await music_client.play(track)

    bot.run('token')

Bot Example
------------

bot example are available in here_.

.. _here: https://github.com/mansuf/discord-ext-music/blob/main/example/bot.py