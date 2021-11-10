"""
A simple music bot in Python using discord-ext-music library
"""

import discord
import argparse
import asyncio
import os
import youtube_dl
from typing import Any, Dict, Tuple, Union
from youtube_search_requests import AsyncYoutubeSearch, AsyncYoutubeSession
from discord.ext.commands import Bot, Context
from discord.ext.music.voice_client import MusicClient
from discord.ext.music.track import Track
from discord.ext.music.voice_source.av import LibAVOpusAudio
from discord.ext.music.utils.errors import IllegalSeek, MusicNotPlaying, NoMoreSongs

# Set prefix
_env_prefix = os.environ.get('PREFIX')
prefix = '$' if not _env_prefix else _env_prefix

# Set up asyncio event loop
loop = asyncio.get_event_loop()

# Initation YoutubeDL
youtube = youtube_dl.YoutubeDL({'format': 'best'})

# Initiation youtube search
youtube_search_session = AsyncYoutubeSession()
youtube_search = AsyncYoutubeSearch(youtube_search_session)

# Configure intents
intents = discord.Intents.default()

# Initiation Client
client = Bot(prefix, intents=intents)

# Speed up search and get stream url from youtube_dl
def _get_stream_url(url):
    info = youtube.extract_info(url, download=False)
    return info, info['url']

async def get_stream_url(query: str) -> Tuple[bool, Union[None, Dict[str, Any]], Union[None, str]]:
    # Check if query is valid url
    if query.startswith('https://') or query.startswith('http://'):
        info, stream_url = await loop.run_in_executor(None, lambda: _get_stream_url(query))
        return True, info, stream_url
    results = await youtube_search.search_videos(query, max_results=1, timeout=3)
    if not results:
        return False, None, None
    result = results[0]
    info, stream_url = await loop.run_in_executor(None, lambda: _get_stream_url(result['url']))
    return True, info, stream_url

# Utilitys

def get_voice_bot(guild: discord.Guild) -> Union[None, MusicClient]:
    """Get connected voice bot (if exist)"""
    for voice in client.voice_clients:
        if voice.guild.id == guild.id:
            return voice

def check_voice_permissions(perms: discord.Permissions) -> Tuple[bool, Union[None, str]]:
    """Check voice permissions"""
    words = ''
    if not perms.connect:
        words += 'Connect, '
    if not perms.speak:
        words += 'Speak'
    if not words:
        return True, None
    else:
        return False, words

async def get_voice_user(ctx: Context) -> Union[bool, discord.VoiceChannel, MusicClient]:
    """Get connected voice user"""
    # Get voice user
    voice_user = ctx.message.author.voice

    # If user is not connected to voice, throw error
    # To prevent users have playback controls outside voice channels
    if not voice_user:
        await ctx.send('You must connected to voice to use this command')
        return False

    # Get voice bot (if connected)
    voice_bot = get_voice_bot(voice_user.channel.guild)
    if voice_bot:

        # If bot is connected to voice channel but user connected to different voice channel
        # Throw error
        if voice_user.channel.id != voice_bot.channel.id:
            await ctx.send(f'{client.user.name} is being used in another voice channel')
            return False

        # Bot and user are connected to same voice channel and
        # We already connected to voice
        return voice_bot

    # Check bot permissions for connected user voice channel
    joinable, missing_perms = check_voice_permissions(voice_user.channel.permissions_for(ctx.me))

    # If not not enough permissions tell the user
    # That bot has not enough permissions
    if not joinable:
        await ctx.send(f'I don\'t have permissions `{missing_perms}` in <#{str(voice_user.id)}>')
        return False
    return voice_user.channel

async def connect_music_client(ctx: Context, channel: discord.VoiceChannel, timeout: int=60) -> Union[bool, MusicClient]:
    """Connect to voice channel, return :class:`MusicClient`"""
    try:
        music_client = await channel.connect(timeout=timeout, cls=MusicClient)
    except asyncio.TimeoutError:
        # Failed to connect, Timeout occured
        await ctx.send('Failed to connect to <#%s> (Timeout)' % channel.id)
        return False
    else:
        return music_client

async def get_music_client(ctx: Context) -> Union[bool, MusicClient]:
    """Retrieve :class:`MusicClient`, create one if necessary"""
    # Retrieve voice channel that user connected to
    voice_user = await get_voice_user(ctx)

    if isinstance(voice_user, discord.VoiceChannel):
        # Initialize and connect MusicClient
        music_client = await connect_music_client(ctx, voice_user)
    else:
        # We already conencted to voice channel
        music_client = voice_user
    return music_client

async def announce_next_song(err: Exception, track: Track):
    """Announce the next song"""
    # If playlist is reached the end of tracks
    # do nothing
    if not track:
        return

    channel = track.channel
    user_id = track.user_id

    # If error detected, tell the user that bot has trouble playing this song
    if err:
        embed = discord.Embed()
        embed.add_field(name='Failed to play song', value='[%s](%s) [<@!%s>]\nError: `%s`' % (
            track.name,
            track.url,
            user_id,
            str(err)
        ))

    # Send the announcer
    embed = discord.Embed()
    embed.set_thumbnail(url=track.thumbnail)
    embed.add_field(name='Now playing', value='[%s](%s) [<@!%s>]' % (
        track.name,
        track.url,
        user_id,
    ))
    await channel.send(embed=embed)

# Play command
@client.command()
async def play(ctx: Context, *, query):
    # Retrieve music client
    music_client = await get_music_client(ctx)

    # We're failed to connect to voice channel
    if not music_client:
        return

    # Set announcer
    music_client.register_after_callback(announce_next_song)

    # Get stream url (if success)
    success, info, stream_url = await get_stream_url(query)
    if not success:
        return await ctx.send('`%s` cannot be found' % query)

    # Create track
    track = Track(
        LibAVOpusAudio(stream_url),
        info['title'],
        info['webpage_url'],
        info['url'],
        info['thumbnail'],
        channel=ctx.channel, # Text channel for annouce the next song
        user_id=ctx.message.author.id # User that request this song
    )

    # Normally when you call MusicClient.play() it automatically add to playlist
    # even it still playing songs
    # So we need to check if MusicClient is still playing or not
    # to tell the user that this song will be put in queue
    if music_client.is_playing():
        embed = discord.Embed()
        embed.set_thumbnail(url=info['thumbnail'])
        embed.add_field(name='Added to queue', value='[%s](%s) [<@!%s>]' % (
            info['title'],
            info['webpage_url'],
            ctx.message.author.id
        ))
        await ctx.send(embed=embed)
        await music_client.play(track)
        return

    # Play the music !!
    await music_client.play(track)

    # Sending message that we're playing song
    embed = discord.Embed()
    embed.set_thumbnail(url=info['thumbnail'])
    embed.add_field(name='Now Playing', value='[%s](%s) [<@!%s>]' % (
        info['title'],
        info['webpage_url'],
        ctx.message.author.id
    ))
    await ctx.send(embed=embed)

# Stop command
@client.command()
async def stop(ctx: Context):
    # Retrieve music client
    music_client = await get_music_client(ctx)

    # We're failed to connect to voice channel
    if not music_client:
        return

    # Check if we're playing or not
    # If not, tell user that bot is not playing anything
    if not music_client.is_playing():
        return await ctx.send(f'{client.user.name} not playing audio')

    # Stop the music    
    await music_client.stop()
    await ctx.send('Stopped')

# Pause command
@client.command()
async def pause(ctx: Context):
    # Retrieve music client
    music_client = await get_music_client(ctx)

    # We're failed to connect to voice channel
    if not music_client:
        return

    # Check if we're playing or not
    # If not, tell user that bot is not playing anything
    if not music_client.is_playing():
        return await ctx.send(f'{client.user.name} not playing audio')

    # Pause the music
    await music_client.pause()
    await ctx.send('Paused')

# Resume command
@client.command()
async def resume(ctx: Context):
    # Retrieve music client
    music_client = await get_music_client(ctx)

    # We're failed to connect to voice channel
    if not music_client:
        return

    # Check if we're playing or not
    # If yes, tell user that bot is already playing audio
    if music_client.is_playing():
        return await ctx.send(f'{client.user.name} already playing audio')

    # Check that we're not paused
    if not music_client.is_paused():
        return await ctx.send(f'{client.user.name} is not in paused state')

    # Resume the music
    await music_client.resume()
    await ctx.send('Resumed')

# Seek command
@client.command()
async def seek(ctx: Context, _num):
    # Check given number is valid number
    try:
        number = float(_num)
    except ValueError:
        # Not a number
        return await ctx.send('Not a number')

    # Retrieve music client
    music_client = await get_music_client(ctx)

    # We're failed to connect to voice channel
    if not music_client:
        return

    # Check if we're playing or not
    # If not, tell user that bot is not playing anything
    if not music_client.is_playing():
        return await ctx.send(f'{client.user.name} not playing audio')

    # Check that we're paused
    if music_client.is_paused():
        return await ctx.send(f'{client.user.name} is in paused state')

    # Begin seeking process
    try:
        await music_client.seek(number)
    except IllegalSeek:
        # Current stream does not support seeking
        await ctx.send('Current playing audio does not support seeking')
    else:
        await ctx.send('Jumped forward to %s seconds' % number)

# Rewind command
@client.command()
async def rewind(ctx: Context, _num):
    # Check given number is valid number
    try:
        number = float(_num)
    except ValueError:
        # Not a number
        return await ctx.send('Not a number')

    # Retrieve music client
    music_client = await get_music_client(ctx)

    # We're failed to connect to voice channel
    if not music_client:
        return

    # Check if we're playing or not
    # If not, tell user that bot is not playing anything
    if not music_client.is_playing():
        return await ctx.send(f'{client.user.name} not playing audio')

    # Check that we're paused
    if music_client.is_paused():
        return await ctx.send(f'{client.user.name} is in paused state')

    # Begin rewind process
    try:
        await music_client.rewind(number)
    except IllegalSeek:
        # Current stream does not support seeking
        await ctx.send('Current playing audio does not support seeking')
    else:
        await ctx.send('Jumped backward to %s seconds' % number)

# Skip / next_song command
@client.command()
async def skip(ctx: Context):
    # Retrieve music client
    music_client = await get_music_client(ctx)

    # We're failed to connect to voice channel
    if not music_client:
        return

    # Skip to next song
    try:
        await music_client.next_track()
    except NoMoreSongs:
        # Playlist has reached at the end
        await ctx.send('There is no more next songs in playlist')
    else:
        track = music_client.track
        embed = discord.Embed()
        embed.set_thumbnail(url=track.thumbnail)
        embed.add_field(name='Now Playing', value='[%s](%s) [<@!%s>]' % (
            track.name,
            track.url,
            ctx.message.author.id
        ))
        await ctx.send(embed=embed)

# Back / previous_song command
@client.command()
async def back(ctx: Context):
    # Retrieve music client
    music_client = await get_music_client(ctx)

    # We're failed to connect to voice channel
    if not music_client:
        return

    # Skip to next song
    try:
        await music_client.previous_track()
    except NoMoreSongs:
        # Playlist has reached at the end
        await ctx.send('There is no more next songs in playlist')
    else:
        track = music_client.track
        embed = discord.Embed()
        embed.set_thumbnail(url=track.thumbnail)
        embed.add_field(name='Now Playing', value='[%s](%s) [<@!%s>]' % (
            track.name,
            track.url,
            ctx.message.author.id
        ))
        await ctx.send(embed=embed)

# on_connect() event
@client.event
async def on_connect():
    # Create new session on AsyncYoutubeSearch
    await youtube_search_session.new_session()

# on_ready() event
@client.event
async def on_ready():
    # Change presence
    activity = discord.Activity(type=discord.ActivityType.listening)
    activity.name = f'My prefix is {prefix}'
    await client.change_presence(activity=activity)
    print(f'{client.user.name} is Ready !!, with prefix "{prefix}"')

if __name__ == "__main__":
    # Parse the arguments
    parser = argparse.ArgumentParser('discord-ext-music example bot')
    parser.add_argument('--token', help='Discord bot token', required=True)
    args = parser.parse_args()

    # Run the bot
    loop.run_until_complete(client.start(args.token))

