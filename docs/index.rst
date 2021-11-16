.. discord-ext-music documentation master file, created by
   sphinx-quickstart on Sun Aug 15 22:26:51 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to discord-ext-music's documentation!
=============================================

An easy to use music extension for discord.py_

Features:
----------

- It's easy to use and can be used for complex process.
- Complete playback controls and thread-safe.
- The audio source can be used in discord.py_ audio library.

.. _discord.py: https://github.com/Rapptz/discord.py

Quick Usage
------------

.. code-block:: python3

    from discord.ext.commands import Bot
    from discord.ext.music import MusicClient, WAVAudio, Track

    bot = Bot()

    @bot.command()
    async def play(ctx):
        voice_user = ctx.message.author.voice
        music_client = await voice_user.channel.connect(cls=MusicClient)
        track = Track(
            WAVAudio('audio.wav'), # AudioSource
            'This is audio' # name
        )
        await music_client.play(track)

    bot.run('token')

Links
------

.. toctree::
   :glob:
   :maxdepth: 2

   installation
   api

.. toctree::
   :hidden:
   :caption: Development

   changelog
   Github repository <https://github.com/mansuf/discord-ext-music>

