import queue
import sys
import discord
import asyncio
import logging
import audioop
import shlex
import json
import io
import re
import time
from io import IOBase
from discord.opus import _OpusStruct as OpusEncoder
from asyncio import subprocess
from ..utils.errors import IllegalSeek
from .oggparse import AsyncOggStream
from ..worker import QueueWorker
from ..equalizer import PCMEqualizer

# This was used for RawPCMAudio source
pcm_worker = QueueWorker(max_limit_job=5)

if sys.platform != 'win32':
    CREATE_NO_WINDOW = 0
else:
    CREATE_NO_WINDOW = 0x08000000

log = logging.getLogger(__name__)

class MusicSource(discord.AudioSource):
    """
    same like :class:`discord.AudioSource`, but its have
    seek, rewind, and volume built-in to AudioSource
    """
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
        raise False

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

    def set_volume(self, volume: float):
        """
        Set volume in float percentage

        For example, 0.5 = 50%, 1.5 = 150%
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

    Parameters
    ------------
    data: :class:`IOBase`
        file-like object
    volume: :class:`float` (Optional, default: `0.5`)
        Set initial volume for AudioSource
    eq_stabilize: :class:``

    Attributes
    -----------
    stream: :term:`py:file object`
        A file-like object that reads byte data representing raw PCM.

    Raises
    --------
    IllegalSeek
        current stream doesn't support seek() operations
    """
    def __init__(
        self,
        stream: IOBase,
        volume: float=0.5,
        eq_stabilize: bool=True,
        worker: QueueWorker=None
    ):
        self.stream = stream
        self._durations = 0
        self._eq = None
        self._stabilize = eq_stabilize
        self._worker = worker
        self._buffered_eq = None
        self._buffered_eq_queue = queue.Queue(20)
        self._volume = max(volume, 0.0)

    def read(self):
        while True:
            if self._eq is not None:
                # At this point if AudioSource using PCMEqualizer,
                # the equalizer cannot convert audio if duration is too small (ex: 20ms)
                # they will reproduce weird sound.
                # So the AudioSource must read audio data at least for 1 second
                # and then equalize it and move it to buffered equalized audio data.
                # The MusicPlayer will read audio data from buffered equalized audio data.

                def equalize(self, result=False):
                    # The source will read the stream at least 1 second duration
                    data = self.stream.read(OpusEncoder.FRAME_SIZE * 50) # 1 second duration

                    # Return "exhausted" bytes to prevent re-reading stream
                    if not data:
                        return io.BytesIO(b'exhausted')

                    # And then convert / equalize it
                    eq_data = self._eq.convert(data)

                    # Store it in buffered equalized audio data
                    buffered_eq = io.BytesIO(eq_data)

                    if result:
                        return buffered_eq

                    try:
                        self._buffered_eq_queue.put_nowait(buffered_eq)
                    except queue.Full:
                        pass

                worker = self._worker or pcm_worker
                if self._buffered_eq is None:
                    # If :param:`eq_stabilize` is set to `True`
                    # Equalizing audio data will be done in another :class:`QueueWorker`
                    if self._stabilize:
                        fut = worker.submit_nowait(lambda: equalize(self))
                        self._buffered_eq = self._buffered_eq_queue.get()
                    else:
                        self._buffered_eq = equalize(self, True)

                # Read the buffered equalized audio data
                data = self._buffered_eq.read(OpusEncoder.FRAME_SIZE)
                
                if not data:
                    self._buffered_eq = None
                    continue
                elif len(data) != OpusEncoder.FRAME_SIZE:
                    return b''
                self._durations += 0.020 # 20ms
                return audioop.mul(data, 2, min(self._volume, 2.0))
            else:
                if self._buffered_eq is not None:
                    # Make sure that buffered eq is exhausted
                    data = self._buffered_eq.read(OpusEncoder.FRAME_SIZE)
                    if not data:
                        self._buffered_eq = None
                        continue
                else:
                    data = self.stream.read(OpusEncoder.FRAME_SIZE)
                if len(data) != OpusEncoder.FRAME_SIZE:
                    return b''
                self._durations += 0.020 # 20ms
                return audioop.mul(data, 2, min(self._volume, 2.0))
    
    def cleanup(self):
        self.stream.close()

    def seekable(self):
        return self.stream.seekable()

    def get_stream_durations(self):
        return self._durations

    def set_volume(self, volume: float):
        self._volume = max(volume, 0.0)

    def set_equalizer(self, eq: PCMEqualizer=None):
        self._eq = eq

    # -------------------------------------------
    # Formula seek and rewind for PCM-based Audio
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
        self._durations = s_pos / 1000 * 20 / OpusEncoder.FRAME_SIZE

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

        # This was used for seek(), set_volume() and rewind() operations
        # when one of that method is being called
        # another one method will be blocked until is finished
        # because this audio source stream cannot be seek() directly
        # it can be manipulated by changing source with seek argument
        self._lock = asyncio.Lock()

        args = [*args]
        kwargs = {'stdout': asyncio.subprocess.PIPE, 'loop': loop}
        kwargs.update(subprocess_kwargs)

        self._executable = executable
        self._kwargs = kwargs
        self._args = args

    async def _spawn_process(self, args, **kwargs):
        process = None
        try:
            process = await asyncio.create_subprocess_exec(
                self._executable,
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

    def get_stream_durations(self):
        return self._durations

    def is_async(self):
        return True

    def seekable(self):
        # always return True
        return True

    async def set_volume(self, volume: float):
        async with self._lock:
            # Store the current source to old source
            old_source = self._process

            # Create silence source and move it to current source
            # we're using AsyncSilence because Silence read() doesn't support async
            self._stdout = AsyncSilence()

            # Kill the old source
            old_source.kill()

            # FFmpeg volume options
            options = '-filter:a "volume=%s"' % volume

            # Modify the parameters
            args = self._args[1:]
            vol_opts = shlex.split(options)
            self._args = [self._executable] + args + vol_opts

            # re-create the ffmpeg
            await self.spawn()

            self._volume = volume

    # ----------------------------------------------
    # Formula seek and rewind for AsyncFFmpegAudio
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
    # Formula seek and rewind for AsyncFFmpegAudio
    # 
    # [*] First, give seconds (from how many you want to seek and rewind
    # as a parameter for seek() and rewind().
    # [*] Second, Move current source to old source, 
    # create Silence() and move it to current source
    # [*] Third, Kill the old source.
    # [*] Fourth, convert seconds and self._durations to a readable
    # time string (00:00:00) using time module.
    # [*] Fifth, Create new subprocess ffmpeg with seek argument from 
    # readable time string.
    # [*] Sixth, move the new AsyncFFmpegAudio to the current source.
    # [*] Seventh, Done.

    async def seek(self, seconds: float):
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
            args = self._args[1:]
            seek_opts = shlex.split(options)
            self._args = [self._executable] + seek_opts + args

            # re-create the ffmpeg
            await self.spawn()

            # Change current stream durations
            self._durations += seconds

    async def rewind(self, seconds: float):
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
            args = self._args[1:]
            seek_opts = shlex.split(options)
            self._args = [self._executable] + seek_opts + args

            # re-create the ffmpeg
            await self.spawn()

            # Change current stream durations
            self._durations -= seconds

    def __del__(self):
        asyncio.ensure_future(self.cleanup())

class AsyncFFmpegPCMAudio(AsyncFFmpegAudio):
    """
    An audio source from FFmpeg (or AVConv).

    This launches a sub-process to a specific input file given.

    .. warning::
        You must have the ffmpeg or avconv executable in your path environment
        variable in order for this to work.

    Note
    ------
    You will have to call `spawn()` in order for this to work.

    The asyncio event loop must support subprocess,
    see https://docs.python.org/3/library/asyncio-platforms.html#asyncio-windows-subprocess.

    Parameters
    ------------
    source: Union[:class:`str`, :class:`io.BufferedIOBase`]
        The input that ffmpeg will take and convert to PCM bytes.
        If ``pipe`` is ``True`` then this is a file-like object that is
        passed to the stdin of ffmpeg.
    executable: :class:`str`
        The executable name (and path) to use. Defaults to ``ffmpeg``.
    volume: :class:`float`
        Set initial volume for AudioSource, defaults to `0.5`
    loop: :class:`asyncio.AbstractEventLoop`
        The asyncio event loop, defaults to `None`
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
        volume=0.5,
        loop=None,
        pipe=False,
        stderr=None,
        before_options=None,
        options=None
    ):
        self._durations = 0
        self._volume = volume

        # This was used for seek(), set_volume() and rewind() operations
        # when one of that method is being called
        # another one method will be blocked until is finished
        # because this audio source stream cannot be seek() directly
        # it can be manipulated by changing source with seek argument
        self._lock = asyncio.Lock()

        args = []
        subprocess_kwargs = {'stdin': source if pipe else asyncio.subprocess.DEVNULL, 'stderr': stderr}

        if isinstance(before_options, str):
            args.extend(shlex.split(before_options))

        args.append('-i')
        args.append('-' if pipe else source)
        args.extend(('-filter:a', 'volume=%s' % volume))
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

    def is_opus(self):
        return False

class AsyncFFmpegOpusAudio(AsyncFFmpegAudio):
    """
    Same like :class:`discord.player.FFmpegOpusAudio`, but it doesn't accept `codec` paramater.

    An audio source from FFmpeg (or AVConv).

    This launches a sub-process to a specific input file given.  However, rather than
    producing PCM packets like :class:`FFmpegPCMAudio` does that need to be encoded to
    Opus, this class produces Opus packets, skipping the encoding step done by the library.

    .. versionadded:: 1.3

    .. warning::

        You must have the ffmpeg or avconv executable in your path environment
        variable in order for this to work.

    Note
    ------
    You will have to call `spawn()` in order for this to work.

    The asyncio event loop must support subprocess,
    see https://docs.python.org/3/library/asyncio-platforms.html#asyncio-windows-subprocess.

    Parameters
    ------------
    source: Union[:class:`str`, :class:`io.BufferedIOBase`]
        The input that ffmpeg will take and convert to Opus bytes.
        If ``pipe`` is ``True`` then this is a file-like object that is
        passed to the stdin of ffmpeg.
    bitrate: :class:`int`
        The bitrate in kbps to encode the output to.  Defaults to ``128``.
    executable: :class:`str`
        The executable name (and path) to use. Defaults to ``ffmpeg``.
    volume: :class:`float`
        Set initial volume for AudioSource, defaults to `0.5`
    loop: :class:`asyncio.AbstractEventLoop`
        The asyncio event loop, defaults to `None`
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
        bitrate=128,
        executable='ffmpeg',
        volume=0.5,
        loop=None,
        pipe=False,
        stderr=None,
        before_options=None,
        options=None
    ):
        self._durations = 0
        self._volume = volume

        args = []
        subprocess_kwargs = {'stdin': source if pipe else asyncio.subprocess.DEVNULL, 'stderr': stderr}

        if isinstance(before_options, str):
            args.extend(shlex.split(before_options))

        args.append('-i')
        args.append('-' if pipe else source)

        args.extend(('-filter:a', 'volume=%s' % volume))
        args.extend(('-map_metadata', '-1',
                     '-f', 'opus',
                     '-ar', '48000',
                     '-ac', '2',
                     '-b:a', '%sk' % bitrate,
                     '-loglevel', 'warning'))

        if isinstance(options, str):
            args.extend(shlex.split(options))

        args.append('pipe:1')

        super().__init__(source, executable=executable, loop=loop, args=args, **subprocess_kwargs)

    @classmethod
    async def from_probe(cls, source, *, method=None, **kwargs):
        """|coro|

        A factory method that creates a :class:`AsyncFFmpegOpusAudio` after probing
        the input source for audio codec and bitrate information.

        You will no need to call `spawn()` after calling this function,
        this function will automatically call `spawn()` after probing.

        Examples
        ----------

        Use this function to create an :class:`AsyncFFmpegOpusAudio` instance instead of the constructor: ::

            source = await discord.AsyncFFmpegOpusAudio.from_probe("song.webm")
            voice_client.play(source)

        If you are on Windows and don't have ffprobe installed, use the ``fallback`` method
        to probe using ffmpeg instead: ::

            source = await discord.AsyncFFmpegOpusAudio.from_probe("song.webm", method='fallback')
            voice_client.play(source)

        Using a custom method of determining bitrate: ::

            # NOTE: custom method must be coroutine function otherwise it will raise error

            async def custom_probe(source, executable):
                # some analysis code here

                return bitrate

            source = await discord.AsyncFFmpegOpusAudio.from_probe("song.webm", method=custom_probe)
            voice_client.play(source)

        Parameters
        ------------
        source
            Identical to the ``source`` parameter for the constructor.
        method: Optional[Union[:class:`str`, Callable[:class:`str`, :class:`str`]]]
            The probing method used to determine bitrate and codec information. As a string, valid
            values are ``native`` to use ffprobe (or avprobe) and ``fallback`` to use ffmpeg
            (or avconv).  As a callable, it must take two string arguments, ``source`` and
            ``executable``.  Both parameters are the same values passed to this factory function.
            ``executable`` will default to ``ffmpeg`` if not provided as a keyword argument.
        kwargs
            The remaining parameters to be passed to the :class:`AsyncFFmpegOpusAudio` constructor,
            excluding ``bitrate``.

        Raises
        --------
        AttributeError
            Invalid probe method, must be ``'native'`` or ``'fallback'``.
        TypeError
            Invalid value for ``probe`` parameter, must be :class:`str` or a callable.

        Returns
        --------
        :class:`AsyncFFmpegOpusAudio`
            An instance of this class.
        """

        executable = kwargs.get('executable')
        bitrate = await cls.probe(source, method=method, executable=executable)
        probe = cls(source, bitrate=bitrate, **kwargs)
        await probe.spawn()
        return probe

    @classmethod
    async def probe(cls, source, *, method=None, executable=None):
        """|coro|

        Probes the input source for bitrate and codec information.

        Parameters
        ------------
        source
            Identical to the ``source`` parameter for :class:`FFmpegOpusAudio`.
        method
            Identical to the ``method`` parameter for :meth:`FFmpegOpusAudio.from_probe`.
        executable: :class:`str`
            Identical to the ``executable`` parameter for :class:`FFmpegOpusAudio`.

        Raises
        --------
        AttributeError
            Invalid probe method, must be ``'native'`` or ``'fallback'``.
        TypeError
            Invalid value for ``probe`` parameter, must be :class:`str` or a coroutine function.

        Returns
        ---------
        Tuple[Optional[:class:`str`], Optional[:class:`int`]]
            A 2-tuple with the codec and bitrate of the input source.
        """

        method = method or 'native'
        executable = executable or 'ffmpeg'
        probefunc = fallback = None

        if isinstance(method, str):
            probefunc = getattr(cls, '_probe_codec_' + method, None)
            if probefunc is None:
                raise AttributeError("Invalid probe method '%s'" % method)

            if probefunc is cls._probe_codec_native:
                fallback = cls._probe_codec_fallback

        elif asyncio.iscoroutinefunction(method):
            probefunc = method
            fallback = cls._probe_codec_fallback
        else:
            raise TypeError("Expected str or coroutine function for parameter 'probe', " \
                            "not '{0.__class__.__name__}'" .format(method))

        bitrate = None
        try:
            bitrate = await probefunc(source, executable)
        except Exception:
            if not fallback:
                log.exception("Probe '%s' using '%s' failed", method, executable)
                return

            log.exception("Probe '%s' using '%s' failed, trying fallback", method, executable)
            try:
                bitrate = await fallback(source, executable)
            except Exception:
                log.exception("Fallback probe using '%s' failed", executable)
            else:
                log.info("Fallback probe found bitrate=%s", bitrate)
        else:
            log.info("Probe found bitrate=%s", bitrate)
        finally:
            return bitrate

    @staticmethod
    async def _probe_codec_native(source, executable='ffmpeg'):
        exe = executable[:2] + 'probe' if executable in ('ffmpeg', 'avconv') else executable
        args = ['-v', 'quiet', '-print_format', 'json', '-show_streams', '-select_streams', 'a:0', source]
        proc = await subprocess.create_subprocess_exec(
            exe,
            *args,
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        out, _ = await asyncio.wait_for(proc.communicate(), 20)
        output = out.decode('utf8')
        bitrate = None

        if output:
            data = json.loads(output)
            streamdata = data['streams'][0]

            bitrate = int(streamdata.get('bit_rate', 0))
            bitrate = max(round(bitrate/1000, 0), 512)

        return bitrate

    @staticmethod
    async def _probe_codec_fallback(source, executable='ffmpeg'):
        args = ['-hide_banner', '-i',  source]
        proc = await subprocess.create_subprocess_exec(
            executable,
            *args,
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        out, _ = await asyncio.wait_for(proc.communicate(), 20)
        
        output = out.decode('utf8')
        bitrate = None

        br_match = re.search(r"(\d+) [kK]b/s", output)
        if br_match:
            bitrate = max(int(br_match.group(1)), 512)

        return bitrate

    async def spawn(self):
        await super().spawn()
        stream = AsyncOggStream(self._stdout)
        self._packet_iter = stream.iter_packets()

    async def read(self):
        try:        
            ret = await self._packet_iter.__anext__()
        except StopAsyncIteration:
            return b''
        else:
            self._durations += 0.020 # 20ms
            return ret

    def is_opus(self):
        return True
