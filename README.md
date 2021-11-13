[![pypi-total-downloads](https://img.shields.io/pypi/dm/discord-ext-music?label=DOWNLOADS&style=for-the-badge)](https://pypi.org/project/discord-ext-music)
[![python-ver](https://img.shields.io/pypi/pyversions/discord-ext-music?style=for-the-badge)](https://pypi.org/project/discord-ext-music)
[![pypi-release-ver](https://img.shields.io/pypi/v/discord-ext-music?style=for-the-badge)](https://pypi.org/project/discord-ext-music)

# discord-ext-music

An easy-to-use music extension for [discord.py](https://github.com/Rapptz/discord.py)

## Features

- It's easy to use and can be used for complex process.
- Complete playback controls and thread-safe.
- Built-in equalizer and volume adjuster.
- The audio source can be used in [discord.py](https://github.com/Rapptz/discord.py) audio library.

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

## What type of audio formats discord-ext-music can play ?

basically, you can play these formats without additional packages:
- Raw PCM
- WAV

with [miniaudio](https://github.com/irmen/pyminiaudio) you can play these formats:
- MP3
- FLAC
- **All formats that vorbis encoded**
- WAV

with [PyAV](https://github.com/PyAV-Org/PyAV) you can almost play anything that supported by [ffmpeg](http://ffmpeg.org/) libraries

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

## Links

- [Documentation](http://discord-ext-music.rtfd.io/)
- [PyPI](https://pypi.org/project/discord-ext-music)

## Example

Bot example are available in [here](https://github.com/mansuf/bot-music-discordpy)
