import sys
import discord
import asyncio
import logging
import shlex
import time
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

class AsyncSilence(Silence):
    async def read(self):
        return super().read()

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

        # Change current stream durations
        self._durations = c_pos / 1000 * 20 / OpusEncoder.FRAME_SIZE

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
        seek = int(c_pos)

        # Finally jump to specified positions
        self.stream.seek(seek, 0)

        # Change current stream durations
        self._durations = c_pos / 1000 * 20 / OpusEncoder.FRAME_SIZE

class AsyncFFmpegAudio(MusicSource):
    """
    Same like :class:`discord.player.FFmpegAudio` but its async operations

    unlike :class:`discord.player.FFmpegAudio` when you call `__init__()`,
    it will automatically create :class:`subprocess.Popen`

    in this :class:`AsyncFFmpegAudio` you will have to call `spawn()` to create
    :class:`asyncio.subprocess.Process`
    """

    def __init__(self, source, *, executable='ffmpeg', loop=None, args, **subprocess_kwargs):
        self._process = self._stdout = None
        self._loop = loop or asyncio.get_event_loop()

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
        """
        Initiate ffmpeg subprocess
        """
        try:
            self._process = await self._spawn_process(self._args, **self._kwargs)
        except NotImplementedError:
            raise discord.ClientException('current event loop doesn\'t support subprocess')
        else:
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

    Note
    ------
    you will have to call `spawn()` in order for this to work.

    The asyncio event loop must support subprocess,
    see https://docs.python.org/3/library/asyncio-platforms.html#asyncio-windows-subprocess

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
    """
    def __init__(
        self,
        source,
        *,
        executable='ffmpeg',
        loop=None,
        pipe=False,
        stderr=None,
        before_options=None,
        options=None
    ):
        self._durations = 0
        self._lock = asyncio.Lock()

        # This was used for seek() and rewind() operations
        # when one of that method is being called
        # another one method will be blocked until is finished
        # because this audio source stream cannot be seek() directly
        # it can be manipulated by changing source with seek argument
        self._seek = asyncio.Event()
        self._seek.set()

        args = []
        subprocess_kwargs = {'stdin': source if pipe else asyncio.subprocess.DEVNULL, 'stderr': stderr}

        if isinstance(before_options, str):
            args.extend(shlex.split(before_options))

        args.append('-i')
        args.append('-' if pipe else source)
        args.extend(('-f', 's16le', '-ar', '48000', '-ac', '2', '-loglevel', 'warning'))

        if isinstance(options, str):
            args.extend(shlex.split(options))

        args.append('pipe:1')

        super().__init__(source, executable=executable, loop=loop, args=args, **subprocess_kwargs)

    async def read(self):
        ret = await self._stdout.read(OpusEncoder.FRAME_SIZE)
        if len(ret) != OpusEncoder.FRAME_SIZE:
            return b''
        self._durations += 0.020 # 20ms
        return ret

    def get_stream_durations(self):
        return self._durations

    def is_opus(self):
        return False

    def is_async(self):
        return True

    def seekable(self):
        # always return True
        return True

    # ----------------------------------------------
    # Formula seek and rewind for AsyncFFmpegPCMAudio
    # ----------------------------------------------
    # 
    # NOTE: AsyncFFmpegPCMAudio cannot be seek and rewind
    # because subprocess IO doesn't support seek() and tell()
    # This can be manipulated by re-creating subprocess ffmpeg with seek argument.
    # (-ss "00:00:00")
    # But before re-creating subprocess, place Silence()
    # (for playing silence audio while re-creating subprocess ffmpeg) to old source
    # to prevent errors to the MusicPlayer while playing audio
    #
    # Formula seek and rewind for AsyncFFmpegPCMAudio
    # 
    # [*] First, give seconds (from how many you want to seek and rewind
    # as a parameter for seek() and rewind().
    # [*] Second, Move the old source and create a Silence() source
    # and move the Silence() source to old source.
    # [*] Third, Kill the old source.
    # [*] Fourth, convert seconds and c_seconds arguments to a readable
    # time string (00:00:00) using time module.
    # [*] Fifth, Create new FFmpegPCMAudio with seek argument from 
    # readable time string.
    # [*] Sixth, move the new FFmpegPCMAudio to the old source.
    # [*] Seventh, Done.

    async def seek(self, seconds: float):
        # Wait until rewind() is finished executing
        await self._seek.wait()

        # indicate we are changing source
        self._seek.clear()

        async with self._lock:
            # Store the current source to old source
            old_source = self._process

            # Create silence source and move it to current source
            # we're using AsyncSilence because Silence read() doesn't support async
            self._stdout = AsyncSilence()

            # Kill the old source
            old_source.kill()

            # Convert time to be a readable string
            t = time.gmtime(seconds + self._durations)
            str_time = time.strftime('%H:%M:%S', t)

            # prepare ffmpeg seek options
            options = '-ss %s' % (str_time)

            # Modify the parameters
            self._args = shlex.split(options).extend(self._args)

            # re-create the ffmpeg
            await self.spawn()

        # Indicate that we're done changing source
        self._seek.set()

        # Change current stream durations
        self._durations += seconds

    async def rewind(self, seconds: float):
        # Wait until seek() is finished executing
        await self._seek.wait()

        # indicate we are changing source
        self._seek.clear()

        async with self._lock:
            # Store the current source to old source
            old_source = self._process

            # Create silence source and move it to current source
            # we're using AsyncSilence because Silence read() doesn't support async
            self._stdout = AsyncSilence()

            # Kill the old source
            old_source.kill()

            # Convert time to be a readable string
            t = time.gmtime(self._durations - seconds)
            str_time = time.strftime('%H:%M:%S', t)

            # prepare ffmpeg seek options
            options = '-ss %s' % (str_time)

            # Modify the parameters
            self._args = shlex.split(options).extend(self._args)

            # re-create the ffmpeg
            await self.spawn()

        # Indicate that we're done changing source
        self._seek.set()

        # Change current stream durations
        self._durations -= seconds


        


