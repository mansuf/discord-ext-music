# discord-ext-music

An easy-to-use music extenstion for [discord.py](https://github.com/Rapptz/discord.py)

This project is still in development and not available in PyPI yet.

## Features

- Built-in equalizer and volume adjuster for PCM codec audio
- Built-in Playlist
- Can play most supported sources from ffmpeg libraries and it embedded into python! ([PyAV](https://github.com/PyAV-Org/PyAV) required)



## Installation

Not available yet.

## Supported formats

- Raw PCM
- WAV
- MP3 ([miniaudio](https://github.com/irmen/pyminiaudio) or [PyAV](https://github.com/PyAV-Org/PyAV) required)
- FLAC ([miniaudio](https://github.com/irmen/pyminiaudio) or [PyAV](https://github.com/PyAV-Org/PyAV) required)
- **All formats that vorbis encoded** ([miniaudio](https://github.com/irmen/pyminiaudio) or [PyAV](https://github.com/PyAV-Org/PyAV) required)
- **All formats that [PyAV](https://github.com/PyAV-Org/PyAV) can handle** ([PyAV](https://github.com/PyAV-Org/PyAV) required)

## Supported sources

- Local file
- **All sources that [PyAV](https://github.com/PyAV-Org/PyAV) can handle** ([PyAV](https://github.com/PyAV-Org/PyAV) required)

## Usage

**Dont expect everything is working, this project is still in development**

Official API is not available yet, but you can use this `AudioSource`:
- `RawPCMAudio`
- `WavAudio`
- `MP3toPCMAudio` ([miniaudio](https://github.com/irmen/pyminiaudio) required)
- `FLACtoPCMAudio` ([miniaudio](https://github.com/irmen/pyminiaudio) required)
- `VorbistoPCMAudio` ([miniaudio](https://github.com/irmen/pyminiaudio) required)
- `LibAVOpusAudio` ([PyAV](https://github.com/PyAV-Org/PyAV) required)

from `discord.ext.music.voice_source` for `discord.voice_client.VoiceClient.play()`
