.. currentmodule:: discord.ext.music

Changelog
==========

v0.3.0
-------

Improvements
~~~~~~~~~~~~~

- Optimized PyAV music sources stream.
- Optimized pydub equalizer.

Fix bugs
~~~~~~~~~

- Fixed All of miniaudio music sources malfunctioning when decoding, for more information about what sources are affected see below:
    - :meth:`MP3toPCMAudio.from_file()`
    - :meth:`MP3toPCMAudio.from_data()`
    - :meth:`FLACtoPCMAudio.from_file()`
    - :meth:`FLACtoPCMAudio.from_data()`
    - :meth:`VorbistoPCMAudio.from_file()`
    - :meth:`VorbistoPCMAudio.from_data()`
    - :meth:`WAVtoPCMAudio.from_file()`
    - :meth:`WAVtoPCMAudio.from_data()`
- Fixed :meth:`LibAVOpusAudio.seek()` error caused by unconverted floating numbers.
- Fixed a deadlock when stopping audio caused by :meth:`MusicClient.stop()` is waiting audio player thread to exit.
- Fixed after function is called in audio player when :meth:`MusicClient.stop()` is called.
- Fixed WAVAudio malfunctioning if given stream is valid wav.
- Fixed after function called when voice is disconnected

New features
~~~~~~~~~~~~~

- Added new opus encoder using PyAV_ library.
- Added equalizer support for PyAV-based music source for :class:`LibAVPCMAudio`
- Added :meth:`Playlist.get_pos_from_track()` to retrieve track position from given track
- Added :attr:`MusicSource.volume` property to return current volume.
- Added :attr:`MusicSource.equalizer` property to return current equalizer.
- Added :attr:`MusicClient.playlist` property to retrieve current playlist in `MusicClient`
- Added :meth:`MusicClient.set_playlist()` to set new playlist.
- Added :attr:`MusicClient.volume` property to return current volume from music client.
- Added :meth:`MusicClient.set_volume()` to set volume music source in music client.
- Added :attr:`MusicClient.equalizer` property to return current equalizer from music client.
- Added :meth:`MusicClient.set_equalizer()` to set equalizer in music client.
- Added hook :meth:`MusicClient.on_disconnect()` on MusicClient.
- Added hook :meth:`MusicClient.on_player_error()` on MusicClient.

.. _PyAV: https://github.com/PyAV-Org/PyAV

Breaking changes
~~~~~~~~~~~~~~~~~

- Replaced ``Equalizer`` and ``SubwooferEqualizer`` with :class:`pydubEqualizer` and :class:`pydubSubwooferEqualizer`.
- Removed module ``discord.ext.music.voice_source.av.encoder`` as it unused because new opus encoder.
- Removed ``LibAVAudio`` as it unused.
- Replaced ``LibAVError`` with :class:`StreamHTTPError`
- Removed ``MusicClient.register_after_callback()``, replaced with:
    - :meth:`MusicClient.before_play_next()`
    - :meth:`MusicClient.after_play_next()`
- Removed ``Track.stream_url`` attribute and ``stream_url`` parameter
- Player error handling now are called from :meth:`MusicClient.on_player_error()`

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