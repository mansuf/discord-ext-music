.. currentmodule:: discord.ext.music

API Reference
==============

Music Clients
--------------

MusicClient
~~~~~~~~~~~~

.. autoclass:: MusicClient
    :members:
    :exclude-members: connect, on_voice_state_update

Tracks
------

Track
~~~~~~

.. autoclass:: Track
    :members:

Playlists
----------

Playlist
~~~~~~~~~

.. autoclass:: Playlist
    :members:

Equalizers
-----------

.. autoclass:: Equalizer
    :members:

pydub Equalizer
~~~~~~~~~~~~~~~~

.. autoclass:: pydubEqualizer
    :members:

.. autoclass:: pydubSubwooferEqualizer
    :members:

Music sources
--------------

Legacy music sources
~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: MusicSource
    :members:

.. autoclass:: RawPCMAudio
    :members:

.. autoclass:: WAVAudio
    :members:

Miniaudio music sources
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: Miniaudio
    :members:

.. autoclass:: MP3toPCMAudio
    :members:

.. autoclass:: FLACtoPCMAudio
    :members:

.. autoclass:: VorbistoPCMAudio
    :members:

.. autoclass:: WAVtoPCMAudio
    :members:

PyAV / Embedded FFmpeg libraries music sources
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: LibAVOpusAudio
    :members:

.. autoclass:: LibAVPCMAudio
    :members:

Exceptions
-----------

.. autoexception:: EqualizerError

.. autoexception:: IllegalSeek

.. autoexception:: InvalidMP3

.. autoexception:: InvalidFLAC

.. autoexception:: InvalidVorbis

.. autoexception:: InvalidWAV

.. autoexception:: MiniaudioError

.. autoexception:: StreamHTTPError

.. autoexception:: TrackNotExist

.. autoexception:: MusicClientException

.. autoexception:: MusicNotPlaying

.. autoexception:: MusicAlreadyPlaying

.. autoexception:: NoMoreSongs

.. autoexception:: NotConnected


