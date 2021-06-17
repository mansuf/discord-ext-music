import sys
import discord
import asyncio
import logging
from io import IOBase
from discord.opus import _OpusStruct as OpusEncoder
from .utils.errors import IllegalSeek

if sys.platform != 'win32':
    CREATE_NO_WINDOW = 0
else:
    CREATE_NO_WINDOW = 0x08000000

log = logging.getLogger(__name__)

class MusicSource(discord.AudioSource):
    def is_async(self):
        """
        Check if this source is async or not.
        
        return :class:`bool`
        """
        return False

    def seekable(self):
        """
        Check if this source support seek() and rewind() operations or not

        return :class:`bool`
        """
        raise NotImplementedError()

    def seek(self, seconds: float):
        """
        Jump forward to specified durations
        """
        raise NotImplementedError()
    
    def rewind(self, seconds: float):
        """
        Jump rewind to specified durations
        """
        raise NotImplementedError()

    def get_stream_durations(self):
        """
        Get current stream durations in seconds

        return :class:`float`
        """
        raise NotImplementedError()


class Silence(MusicSource):
    def read(self):
        return bytearray([0xF8, 0xFF, 0xFE])

class RawPCMAudio(MusicSource):
    """Represents raw 16-bit 48KHz stereo PCM audio source.

    Attributes
    -----------
    stream: :term:`py:file object`
        A file-like object that reads byte data representing raw PCM.

    Raises
    --------
    IllegalSeek
        current stream doesn't support seek() operations
    """
    def __init__(self, stream: IOBase):
        self.stream = stream
        self._durations = 0

    def read(self):
        data = self.stream.read(OpusEncoder.FRAME_SIZE)
        if len(data) != OpusEncoder.FRAME_SIZE:
            return b''
        self._durations += 0.020 # 20ms
        return data
    
    def cleanup(self):
        self.stream.close()

    def seekable(self):
        return self.stream.seekable()

    def get_stream_durations(self):
        return self._durations

    # -------------------------------------------
    # Formula seek and rewind for RawPCMAudio
    # -------------------------------------------
    #
    # Finding seekable positions IO
    # ---------------------------------------------------------------------------------------------
    # given_seconds * 1000 / 20 (miliseconds) * OpusEncoder.FRAME_SIZE = seekable positions IO
    # ---------------------------------------------------------------------------------------------
    #
    # Formula seek in seconds
    #
    # Find seekable positions IO and then addition it with IO.tell().
    # The complete formula can be see below
    # -----------------------------------------------------------------------------
    # given_seconds * 1000 / 20 (miliseconds) * OpusEncoder.FRAME_SIZE + IO.tell()
    # -----------------------------------------------------------------------------
    # and then use IO.seek() to jump a specified positions
    #
    # Formula rewind in seconds
    #
    # Find seekable positions IO and then subtract it with IO.tell()
    # The complete formula can be see below
    # -----------------------------------------------------------------------------
    # IO.tell() - given_seconds * 1000 / 20 (miliseconds) * OpusEncoder.FRAME_SIZE
    # -----------------------------------------------------------------------------
    # NOTE: IO.tell() subtraction must be placed in front positions otherwise 
    # the result will be negative.
    # and then use IO.seek() to jump a specified positions

    def seek(self, seconds: float):
        if not self.seekable():
            raise IllegalSeek('current stream doesn\'t support seek() operations')

        # Current stream positions
        c_pos = self.stream.tell()

        # Seekable stream positions
        s_pos = seconds * 1000 / 20 * OpusEncoder.FRAME_SIZE

        # addition it with c_pos
        s_pos += c_pos

        # convert to integer
        # because seek in IO doesn't support float numbers
        seek = int(s_pos)

        # Finally jump to specified positions
        self.stream.seek(seek, 0)

    def rewind(self, seconds: int):
        if not self.seekable():
            raise IllegalSeek('current stream doesn\'t support seek() operations')

        # Current stream positions
        c_pos = self.stream.tell()

        # Seekable stream positions
        s_pos = seconds * 1000 / 20 * OpusEncoder.FRAME_SIZE

        # subtract it with s_pos
        c_pos -= s_pos

        # convert to integer
        # because seek in IO doesn't support float numbers
        seek = int(s_pos)

        # Finally jump to specified positions
        self.stream.seek(seek, 0)

class AsyncFFmpegAudio(MusicSource):
    """
    Same like :class:`discord.player.FFmpegAudio` but its async operations
    and with `seek()` and `rewind()` support

    unlike :class:`discord.player.FFmpegAudio` when you call `__init__()`,
    it will automatically create :class:`subprocess.Popen`

    in this :class:`AsyncFFmpegAudio` you will have to call `spawn()` to create
    :class:`asyncio.subprocess.Process`
    """

    def __init__(self, source, *, executable='ffmpeg', args, **subprocess_kwargs):
        self._process = self._stdout = None

        args = [executable, *args]
        kwargs = {'stdout': asyncio.subprocess.PIPE}
        kwargs.update(subprocess_kwargs)

        self._kwargs = kwargs
        self._args = args

    async def _spawn_process(self, args, **kwargs):
        process = None
        try:
            process = await asyncio.create_subprocess_exec(
                "",
                *args,
                creationflags=CREATE_NO_WINDOW,
                **kwargs
            )
        except FileNotFoundError:
            executable = args.partition(' ')[0] if isinstance(args, str) else args[0]
            raise discord.ClientException(executable + ' was not found.') from None
        except Exception as exc:
            raise discord.ClientException(f'Process failed: {exc.__class__.__name__}: {exc}') from exc
        return process

    async def spawn(self):
        self._process = await self._spawn_process(self._args, **self._kwargs)
        self._stdout = self._process.stdout

    async def cleanup(self):
        proc = self._process
        if proc is None:
            return

        log.info('Preparing to terminate ffmpeg process %s.', proc.pid)

        try:
            proc.kill()
        except Exception:
            log.exception("Ignoring error attempting to kill ffmpeg process %s", proc.pid)

        if proc.returncode is None:
            log.info('ffmpeg process %s has not terminated. Waiting to terminate...', proc.pid)
            await proc.communicate()
            log.info('ffmpeg process %s should have terminated with a return code of %s.', proc.pid, proc.returncode)
        else:
            log.info('ffmpeg process %s successfully terminated with return code of %s.', proc.pid, proc.returncode)

        self._process = self._stdout = None

class AsyncFFmpegPCMAudio(AsyncFFmpegAudio):
    """
    An audio source from FFmpeg (or AVConv).

    This launches a sub-process to a specific input file given.

    .. warning::
        You must have the ffmpeg or avconv executable in your path environment
        variable in order for this to work.

    Parameters
    ------------
    source: Union[:class:`str`, :class:`io.BufferedIOBase`]
        The input that ffmpeg will take and convert to PCM bytes.
        If ``pipe`` is ``True`` then this is a file-like object that is
        passed to the stdin of ffmpeg.
    executable: :class:`str`
        The executable name (and path) to use. Defaults to ``ffmpeg``.
    pipe: :class:`bool`
        If ``True``, denotes that ``source`` parameter will be passed
        to the stdin of ffmpeg. Defaults to ``False``.
    stderr: Optional[:term:`py:file object`]
        A file-like object to pass to the Popen constructor.
        Could also be an instance of ``subprocess.PIPE``.
    before_options: Optional[:class:`str`]
        Extra command line arguments to pass to ffmpeg before the ``-i`` flag.
    options: Optional[:class:`str`]
        Extra command line arguments to pass to ffmpeg after the ``-i`` flag.
        
    Raises
    --------
    ClientException
        The subprocess failed to be created.

    unlike :class:`discord.player.FFmpegAudio` when you call `__init__()`,
    it will automatically create :class:`subprocess.Popen`

    in this :class:`AsyncFFmpegAudio` you will have to call `spawn()` to create
    :class:`asyncio.subprocess.Process`
    """

    pass