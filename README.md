# discord-ext-music

An easy-to-use music extension for [discord.py](https://github.com/Rapptz/discord.py)

## Features

- It's easy to use
- Have all playback and playlist controls (skip, previous, seek, rewind, and etc..)
- Thread-safe playback controls
- Built-in equalizer and volume adjuster for PCM codec audio ([pydub](https://github.com/jiaaro/pydub) and [scipy](https://github.com/scipy/scipy) required)
- Built-in thread-safe playlist
- Can play most supported sources from FFmpeg libraries and it embedded into python! ([PyAV](https://github.com/PyAV-Org/PyAV) required)

## Installation

**Python 3.8 or higher required.**

You can install `discord-ext-music` directly from PyPI by the following command:
```
pip install discord-ext-music
```

If you want to have equalizer support do the following command:
```
pip install discord-ext-music[equalizer]
```

If you want to have miniaudio-based audio source support do the following command:
```
pip install discord-ext-music[miniaudio]
```

If you want to have FFmpeg-based audio source support do the following command:
```
pip install discord-ext-music[pyav]
```

If you want to have all optional dependencies do the following command:
```
pip install discord-ext-music[all]
```

Also, you can install development version by the following command:
```
git clone https://github.com/mansuf/discord-ext-music.git
cd discord-ext-music
pip install -U .[all]
```

### Optional packages
- [scipy](https://github.com/scipy/scipy) and [pydub](https://github.com/jiaaro/pydub)
    (for equalizer support)
- [miniaudio](https://github.com/irmen/pyminiaudio)
    (for miniaudio-based audio source support)
- [PyAV](https://github.com/PyAV-Org/PyAV)
    (for FFmpeg-based audio source support)

## Supported formats

- Raw PCM
- WAV
- MP3 ([miniaudio](https://github.com/irmen/pyminiaudio) or [PyAV](https://github.com/PyAV-Org/PyAV) required)
- FLAC ([miniaudio](https://github.com/irmen/pyminiaudio) or [PyAV](https://github.com/PyAV-Org/PyAV) required)
- **All formats that vorbis encoded** ([miniaudio](https://github.com/irmen/pyminiaudio) or [PyAV](https://github.com/PyAV-Org/PyAV) required)
- **All formats that FFmpeg libraries can handle** ([PyAV](https://github.com/PyAV-Org/PyAV) required)

## Supported sources

- Local file
- **All sources that FFmpeg libraries can handle** ([PyAV](https://github.com/PyAV-Org/PyAV) required)

## Quick usage

**API Documentation coming soon**

```python
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
```

## Example

Bot example are available in directory [`example/bot.py`](https://github.com/mansuf/discord-ext-music/blob/main/example/bot.py)
