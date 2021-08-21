.. currentmodule:: discord.ext.music

Changelog
==========

v0.2.0
-------

New features
~~~~~~~~~~~~~~

- Added `API Documentation`_
- Added :class:`WAVtoPCMAudio` miniaudio-based music sources.
- Added Keyword-arguments only in :class:`Track`, all Keyword-arguments will be setted in :class:`Track` class attributes.

.. _API Documentation: https://discord-ext-music.readthedocs.io/en/stable/index.html

Fixed bugs
~~~~~~~~~~~~

- Fix unhandled error "cannot allocate memory in static TLS block" when importing ``discord.ext.music.voice_source.av`` on ARM-based CPU. **NOTE:** The error is not fixed automatically inside python, because you need to fix it manually outside python. The solution is given inside the error.

Removals
~~~~~~~~~~

- Removed ``WorkerError`` exception class as it unused.
- Removed ``ConverterError`` exception class as it unused.

Improvements
~~~~~~~~~~~~~~

- Improved how next song playback system work in :class:`MusicClient`

Breaking changes
~~~~~~~~~~~~~~~~~~

- Changed module name from ``discord.ext.music.voice_source.pyav`` to ``discord.ext.music.voice_source.av``
- module ``discord.ext.music.equalizer`` no longer raising error when you try to import it.
- module ``discord.ext.music.voice_source.miniaudio`` no longer raising error when you try to import it.
- module ``discord.ext.music.voice_source.av`` no longer raising error when you try to import it.
- Now :class:`PCMEqualizer` and :class:`SubwooferPCMEqualizer` will raise error when you dont have the required modules and try to create it.
- Changed name ``WavAudio`` to :class:`WAVAudio`
- Calling :meth:`LibAVOpusAudio.recreate()` now will close the stream before re-creating it.
- Now ``LibAVAudioStream.seek()`` method will directly seek to the stream instead of re-creating it.

v0.1.0
-------

This is First release of discord-ext-music