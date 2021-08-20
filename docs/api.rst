.. currentmodule:: discord.ext.music

API Reference
==============

Music Clients
--------------

MusicClient
~~~~~~~~~~~~

.. autoclass:: MusicClient
    :members:   add_track, disconnect, get_stream_durations, move_to, next_track, previous_track,
                pause, play, play_track_from_pos, reconnect, register_after_callback, remove_all_tracks,
                remove_track, remove_track_from_pos, resume, rewind, seek, source, stop, track

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

.. autoclass:: PCMEqualizer
    :members:

.. autoclass:: SubwooferPCMEqualizer
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

.. autoclass:: LibAVAudio
    :members:

.. autoclass:: LibAVOpusAudio
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

.. autoexception:: LibAVError

.. autoexception:: TrackNotExist

.. autoexception:: MusicClientException

.. autoexception:: MusicNotPlaying

.. autoexception:: MusicAlreadyPlaying

.. autoexception:: NoMoreSongs

.. autoexception:: NotConnected


