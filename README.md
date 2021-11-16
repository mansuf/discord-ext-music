[![pypi-total-downloads](https://img.shields.io/pypi/dm/discord-ext-music?label=DOWNLOADS&style=for-the-badge)](https://pypi.org/project/discord-ext-music)
[![python-ver](https://img.shields.io/pypi/pyversions/discord-ext-music?style=for-the-badge)](https://pypi.org/project/discord-ext-music)
[![pypi-release-ver](https://img.shields.io/pypi/v/discord-ext-music?style=for-the-badge)](https://pypi.org/project/discord-ext-music)

# discord-ext-music

An easy-to-use music extension for [discord.py](https://github.com/Rapptz/discord.py)

## Key features

- It's easy to use and can be used for complex process.
- Complete playback controls and thread-safe.
- The audio source can be used in [discord.py](https://github.com/Rapptz/discord.py) audio library.
    - **NOTE**: The audio sources from [discord.py](https://github.com/Rapptz/discord.py) cannot be played in [discord-ext-music](https://github.com/mansuf/discord-ext-music) library, see [Reusable audio sources](#reusable-audio-sources)

## Installation

**Python 3.8 or higher required.**

### Stable version

You can install `discord-ext-music` stable version directly from PyPI by the following command:

```bash
pip install discord-ext-music
```

or by the cloning repository with latest stable version:

```bash
git clone --branch v0.3.0 https://github.com/mansuf/discord-ext-music.git
cd discord-ext-music
```

### Development version

You also can install development version by cloning the repository, see below:

```bash
git clone https://github.com/mansuf/discord-ext-music.git
cd discord-ext-music
```

### Optional packages

These are optional packages that you are not required to install it, but you get extra benefit
once you install it.

- [scipy](https://github.com/scipy/scipy) and [pydub](https://github.com/jiaaro/pydub)
    for equalizer support.
- [miniaudio](https://github.com/irmen/pyminiaudio)
    for miniaudio music source support.
- [PyAV](https://github.com/PyAV-Org/PyAV)
    for FFmpeg libraries music source support.

You can install all additional packages in one command:

```bash
pip install discord-ext-music[all]
```

## What type of audio formats discord-ext-music can play ?

basically, you can play these formats without additional packages:
- Raw PCM
- WAV

with [miniaudio](https://github.com/irmen/pyminiaudio), you can play these formats:
- MP3
- FLAC
- **All formats that vorbis encoded**
- WAV

with [PyAV](https://github.com/PyAV-Org/PyAV), you can almost play anything that supported by [ffmpeg](http://ffmpeg.org/) libraries

## What sources that discord-ext-music can play ?

Without additional packages or with [miniaudio](https://github.com/irmen/pyminiaudio) you can only play **local file**.

But, with [PyAV](https://github.com/PyAV-Org/PyAV) you can almost play any sources that supported by [ffmpeg protocols](https://ffmpeg.org/ffmpeg-protocols.html)

## Quick usage

```python
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
```

## Opus encoder

When you're installing discord-ext-music, opus encoder already shipped with it (because of [discord.py]() audio library). This is called native opus encoder good for compatibility and stability. But, if you want to have much better performance and low CPU usage you can use alternative opus encoder using [PyAV](https://github.com/PyAV-Org/PyAV) library (by installing av package `pip install av`).

By default, discord-ext-music auto detect opus encoder. If you have [PyAV](https://github.com/PyAV-Org/PyAV) installed, it will use [PyAV](https://github.com/PyAV-Org/PyAV) opus encoder, otherwise it will use native encoder.

Alternatively, you can set environment to override opus encoder.

For windows:

```bash

# PyAV opus encoder
set OPUS_ENCODER=av

# Native opus encoder
set OPUS_ENCODER=native
```

For linux / Mac OS:

```bash

# PyAV opus encoder
export OPUS_ENCODER=av

# Native opus encoder
export OPUS_ENCODER=native
```

## Notes

### Reusable audio sources

Because discord-ext-music is specialized for music, all audio sources in discord-ext-music are reusable. 
So if you call `MusicClient.stop()`, `MusicClient.next_track()`, `MusicClient.previous_track()`, or `MusicClient.play_track_from_pos()`
the audio source will be recreated with same configurations (**NOTE:** Some audio sources are not reusable, for example: if you pass unseekable stream to `RawPCMAudio` or `WAVAudio` it will become non-reusable). And if the audio ended, the audio sources will not cleaned up, it will stay there until you removed it from playlist or reused by the library. Meanwhile, all audio sources in [discord.py](https://github.com/Rapptz/discord.py) library are not reusable and cannot be played in [`MusicClient`](https://github.com/mansuf/discord-ext-music/blob/main/discord/ext/music/voice_client.py#L26). But, the audio sources in discord-ext-music can be played in [`VoiceClient`](https://github.com/Rapptz/discord.py/blob/v1.7.3/discord/voice_client.py#L171).

### discord-ext-music is not Youtube, Soundcloud, or etc player

To be clear, discord-ext-music is just music extension with: playlist integrated with voice client, equalizer (if you install scipy and pydub), audio playback with thread-safe controls, and audio source that play streamable url. If you want to play youtube stream you must install additional packages like [youtube-dl](https://github.com/ytdl-org/youtube-dl) to extract streamable url and play it under discord-ext-music library.

## Links

- [Documentation](http://discord-ext-music.rtfd.io/)
- [PyPI](https://pypi.org/project/discord-ext-music)