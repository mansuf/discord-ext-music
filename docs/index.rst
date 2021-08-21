.. discord-ext-music documentation master file, created by
   sphinx-quickstart on Sun Aug 15 22:26:51 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to discord-ext-music's documentation!
=============================================

An easy to use music extension for discord.py_

Features:
----------

- It's easy to use
- Have all playback and playlist controls
- Thread-safe playback controls
- Built-in equalizer and volume adjuster for PCM codec audio 
- Can play most supported sources from FFmpeg libraries and it embedded into python! 

.. _discord.py: https://github.com/Rapptz/discord.py

Quick Usage
------------

.. code-block:: python3

    from discord.ext.commands import Bot
    from discord.ext.music import MusicClient, WAVAudio, Track

    bot = Bot()

    @client.command()
    async def play(ctx):
        voice_user = ctx.message.author.voice
        music_client = await voice_user.channel.connect(cls=MusicClient)
        track = Track(
            WAVAudio('audio.wav'), # AudioSource
            'This is audio' # name
        )
        await music_client.play(track)

    bot.run('token')

Bot Example
------------

bot example are available in here_.

.. _here: https://github.com/mansuf/discord-ext-music/blob/main/example/bot.py

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

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
