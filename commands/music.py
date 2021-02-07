import typing
import uuid

import io
import discord
import datetime
import PIL.Image
import PIL.ImageDraw
import discord.ext.commands
import discord.ext.commands
import discord.ext.menus
import lavalink

from utils.exceptions import OutOfBoundVolumeError, VolumeTypeError
from utils.convert import IndexConverter
from utils.convert import PlaylistConverter
from utils.convert import PlaylistPaginator
from utils.convert import SongConverter
from utils.convert import StationConverter
from utils.convert import VolumeConverter
from utils.extensions import DJDiscord, DJDiscordContext
from utils.objects import (
    Playlist,
    BeforeCogInvokeOp,
    AfterCogInvokeOp,
    ErrorOp,
)


def milliseconds_to_str(millis: int) -> str:
    formatted_arr = []

    seconds = (millis / 1000) % 60
    minutes = (millis / (1000 * 60)) % 60
    hours = (millis / (1000 * 60 * 60)) % 24

    if int(hours):
        formatted_arr.append("%d hours" % hours)

    if int(minutes):
        formatted_arr.append("%d minutes" % minutes)

    if int(seconds):
        formatted_arr.append("%d seconds" % seconds)

    return ", ".join(formatted_arr)


class Music(discord.ext.commands.Cog):
    """The voice/music commands that you love"""
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        lavalink.add_event_hook(self.on_track_start,
                                event=lavalink.TrackStartEvent)
        lavalink.add_event_hook(self.on_queue_end,
                                event=lavalink.QueueEndEvent)

    async def on_track_start(self, event: lavalink.TrackStartEvent):
        if event.track.extra["void"]:
            return await event.player.skip()

        embed = discord.Embed(title="Now playing",
                              color=0xDC333C,
                              timestamp=datetime.datetime.now())
        if "thumbnails" in event.track.extra.get("raw_info"):
            embed.add_field(name="Song Title",
                            value=event.track.title,
                            inline=False)
            embed.add_field(name="Song Author",
                            value=event.track.author,
                            inline=False)
            embed.add_field(name="Song Duration",
                            value=milliseconds_to_str(event.track.duration),
                            inline=False)
            embed.add_field(name="Original Link",
                            value="[Click Here](%s)" %
                            event.track.extra["raw_info"]["url"],
                            inline=False)
            embed.set_thumbnail(
                url=event.track.extra["raw_info"]["thumbnails"][-1]["url"])
        else:
            embed.add_field(name="Radio Station Call Sign",
                            value=event.track.extra["raw_info"]["call_sign"],
                            inline=False)
            embed.add_field(name='Radio Station Frequency',
                            value=event.track.extra["raw_info"]["frequency"],
                            inline=False)
            embed.add_field(name="Radio Station Link",
                            value="[Click Here]({})".format(
                                event.track.extra["raw_info"]["url"]),
                            inline=False)
            embed.set_thumbnail(url=event.track.extra["raw_info"]["thumbnail"])
        await event.track.extra["context"].send(embed=embed)

    async def on_queue_end(self, event: lavalink.QueueEndEvent):
        ws = self.bot._connection._get_websocket(event.player.guild_id)
        await ws.voice_state(str(event.player.guild_id), None)

    async def cog_before_invoke(self, ctx: DJDiscordContext) -> None:
        await ctx.trigger_typing()

        if ctx.guild is None:
            return

        if ctx.author.voice is not None:
            await self.ensure_voice(ctx)

        await ctx.database.log(
            BeforeCogInvokeOp(ctx.author, self, ctx.command, ctx.guild,
                              ctx.channel), )

    async def cog_after_invoke(self, ctx: DJDiscordContext) -> None:
        await ctx.database.log(
            AfterCogInvokeOp(ctx.author, self, ctx.command, ctx.guild,
                             ctx.channel), )

    async def cog_command_error(self, ctx: DJDiscordContext,
                                error: Exception) -> None:
        if hasattr(error, "original") and isinstance(error.original, (
                VolumeTypeError,
                OutOfBoundVolumeError,
        )):
            return
        _id = uuid.uuid4()
        await ctx.database.log(ErrorOp(ctx.guild, ctx.channel, ctx.message,
                                       ctx.author),
                               error=error,
                               case_id=_id)
        print(f"An error occurred during command runtime. Case ID: {_id.hex}")

    async def ensure_voice(self, ctx: DJDiscordContext):
        if not ctx.player.is_connected:
            permissions = ctx.author.voice.channel.permissions_for(ctx.me)

            if not permissions.connect or not permissions.speak:  # Check user limit too?
                raise discord.ext.commands.CommandInvokeError(
                    'I need the `CONNECT` and `SPEAK` permissions.')
        else:
            if int(ctx.player.channel_id) != ctx.author.voice.channel.id:
                raise discord.ext.commands.CommandInvokeError(
                    'You need to be in my voicechannel.')

    @discord.ext.commands.command(name="play",
                                  aliases=["begin", "run", "start"])
    async def play(
        self,
        ctx: DJDiscordContext,
        playlist: PlaylistConverter = None,
    ) -> typing.Optional[discord.Message]:
        """Starts a playlist that the user has created, if they haven't created one it will send a message and stop running"""
        if ctx.author.voice is None:
            return await ctx.send(
                "You need to be connected to a channel in order to start playing music"
            )

        if playlist is None:
            playlist = await ctx.database.get(author=ctx.author.id)
            if playlist is None:
                return await ctx.send(
                    "You do not own a playlist nor have specified a playlist to start playing"
                )
            playlist = Playlist.from_json(playlist)

        ws = ctx.bot._connection._get_websocket(ctx.guild.id)
        await ws.voice_state(str(ctx.guild.id),
                             str(ctx.author.voice.channel.id))

        for song in playlist.songs:
            results = await ctx.player.node.get_tracks(song["url"])

            track = lavalink.AudioTrack(results["tracks"][0],
                                        requester=ctx.author.id,
                                        context=ctx,
                                        void=song["void"],
                                        raw_info=song)

            ctx.player.add(requester=ctx.author.id, track=track)

        if not ctx.player.is_playing:
            await ctx.player.play()

    @discord.ext.commands.command(name="rawplay", alias=["rawstart", "rawrun"])
    async def rawplay(self, ctx: DJDiscordContext, *,
                      query: SongConverter) -> None:
        """Starts playing a single song, you can use this command more than once to add to the queue"""
        if ctx.author.voice is None:
            return await ctx.send(
                "You need to be connected to a channel in order to start playing music"
            )

        ws = ctx.bot._connection._get_websocket(ctx.guild.id)
        await ws.voice_state(str(ctx.guild.id),
                             str(ctx.author.voice.channel.id))

        results = await ctx.player.node.get_tracks(query.url)

        track = lavalink.AudioTrack(results["tracks"][0],
                                    requester=ctx.author.id,
                                    context=ctx,
                                    raw_info=query.json)

        ctx.player.add(requester=ctx.author.id, track=track)

        if not ctx.player.is_playing:
            await ctx.player.play()

    @discord.ext.commands.command(name="now")
    async def now(self, ctx: DJDiscordContext) -> None:
        """Sends an embed detailing the specific details of the song/radio station"""
        if ctx.author.voice is None:
            return await ctx.send(
                "You need to join a voice channel to see the current song in the queue"
            )

        if not ctx.player.is_playing:
            return await ctx.send("The bot isn't playing any music")

        if "created" in ctx.player.current.extra.get("raw_info"):
            with io.BytesIO() as buffer:
                im = PIL.Image.open("./assets/progress.png").convert("RGB")
                draw = PIL.ImageDraw.Draw(im)
                per = (ctx.player.position / ctx.player.current.duration) * 600
                draw.ellipse([per, 8, per + 34, 42], fill=(255, 127, 81))
                PIL.ImageDraw.floodfill(im,
                                        xy=(14, 24),
                                        value=(255, 127, 81),
                                        thresh=40)
                im.save(buffer, format="png")
                _file = discord.File(io.BytesIO(buffer.getvalue()),
                                     filename="progress.png")

            await ctx.send(embed=discord.Embed(
                title="Current song in queue",
                color=0xDC333C,
                timestamp=datetime.datetime.now()).add_field(
                    name="Song Name",
                    value=ctx.player.current.extra.get("raw_info")["title"],
                    inline=False).add_field(
                        name="Song Length",
                        value=milliseconds_to_str(ctx.player.current.duration),
                        inline=False).add_field(
                            name="Song Uploader",
                            value=ctx.player.current.extra.get(
                                "raw_info")["uploader"],
                            inline=False).add_field(
                                name="Original Link",
                                value="[Click Me!]({})".format(
                                    ctx.player.current.extra.get("raw_info")
                                    ["url"]),
                                inline=False).
                           set_thumbnail(url=ctx.player.current.extra.get(
                               "raw_info")["thumbnails"][-1]["url"]).set_image(
                                   url="attachment://progress.png"),
                           file=_file)
        else:
            await ctx.send(
                embed=discord.Embed(title="Current radio station",
                                    color=0xDC333C,
                                    timestamp=datetime.datetime.now()).
                add_field(name="Radio Station Call Sign",
                          value=ctx.player.current.extra.get("raw_info")
                          ["call_sign"],
                          inline=False).
                add_field(name="Radio station Frequency",
                          value=ctx.player.current.extra.get("raw_info")
                          ["frequency"],
                          inline=False).add_field(name="Original Link",
                                                  value=ctx.player.current.
                                                  extra.get("raw_info")["url"],
                                                  inline=False).
                set_thumbnail(
                    url=ctx.player.current.extra.get("raw_info")["thumbnail"]))

    @discord.ext.commands.command(name="radiostart")
    async def radiostart(
            self, ctx: DJDiscordContext,
            station: StationConverter) -> typing.Optional[discord.Message]:
        """Starts playing a radio station"""
        if ctx.author.voice is None:
            return await ctx.send(
                "You need to be connected to a channel in order to start playing music"
            )

        if station is None:
            return await ctx.send(
                "You have not specified a valid radio station to start playing"
            )

        ws = ctx.bot._connection._get_websocket(ctx.guild.id)
        await ws.voice_state(str(ctx.guild.id),
                             str(ctx.author.voice.channel.id))

        results = await ctx.player.node.get_tracks(station.source)

        track = lavalink.AudioTrack(results["tracks"][0],
                                    requester=ctx.author.id,
                                    context=ctx,
                                    raw_info=station.json)

        ctx.player.add(track=track, requester=ctx.author.id)

        if not ctx.player.is_playing:
            await ctx.player.play()

    @discord.ext.commands.command(name="volume")
    async def volume(self, ctx: DJDiscordContext,
                     volume: VolumeConverter) -> None:
        """Sets the volume of the music player, min - 0, max - 200"""
        if ctx.author.voice is None:
            return await ctx.send(
                "You need to be connected to a channel in order to change the volume"
            )

        if not ctx.player.is_playing:
            return await ctx.send("The bot isn't playing any music")

        await ctx.player.set_volume(volume)

        return await ctx.send("Set volume to {}%".format(volume))

    @volume.error
    async def _volume_error_handler(self, ctx: DJDiscordContext,
                                    error: Exception) -> None:
        if isinstance(error, discord.ext.commands.ConversionError):
            if isinstance(error.original, VolumeTypeError):
                return await ctx.send("You didn't specify a valid number")
            if isinstance(error.original, OutOfBoundVolumeError):
                return await ctx.send(
                    "You need to select a volume between 0 and 200")

    @discord.ext.commands.command(name="skip")
    async def skip(self,
                   ctx: DJDiscordContext) -> typing.Optional[discord.Message]:
        """Skips the current song, if it's playing a radio station, it will leave the voice channel"""
        if ctx.author.voice is None:
            return await ctx.send(
                "You need to be connected to a channel in order to skip music")

        if not ctx.author.voice or (
                ctx.player.is_connected
                and ctx.author.voice.channel.id != int(ctx.player.channel_id)):
            return await ctx.send('You\'re not in my voicechannel!')

        if not ctx.player.is_playing:
            return await ctx.send("The bot isn't playing any music")

        await ctx.player.skip()

    @discord.ext.commands.command(name="loop")
    async def loop(self,
                   ctx: DJDiscordContext) -> typing.Optional[discord.Message]:
        """Loops the current song playing, if it's playing a radio station, it will do nothing"""
        if ctx.author.voice is None:
            return await ctx.send(
                "You need to be connected to a channel in order to skip music")

        if not ctx.author.voice or (
                ctx.player.is_connected
                and ctx.author.voice.channel.id != int(ctx.player.channel_id)):
            return await ctx.send('You\'re not in my voicechannel!')

        if not ctx.player.is_playing:
            return await ctx.send("The bot isn't playing any music")

        ctx.player.set_repeat(not ctx.player.repeat)

        await ctx.send("Looped the queue")

    @discord.ext.commands.command(name="stop",
                                  aliases=["end", "interrupt", "sigint"])
    async def stop(self,
                   ctx: DJDiscordContext) -> typing.Optional[discord.Message]:
        """Stops playing the current song and clears the queue"""
        if ctx.author.voice is None:
            return await ctx.send(
                "You need to be connected to a channel in order to stop music")

        if not ctx.player.is_playing:
            return await ctx.send("The bot isn't playing any music")

        if not ctx.author.voice or (
                ctx.player.is_connected
                and ctx.author.voice.channel.id != int(ctx.player.channel_id)):
            return await ctx.send('You\'re not in my voicechannel!')

        ctx.player.queue.clear()
        await ctx.player.stop()
        ws = ctx.bot._connection._get_websocket(ctx.guild.id)
        await ws.voice_state(str(ctx.guild.id), None)
        return await ctx.send(embed=discord.Embed(
            title="Destroyed the queue and released voice channel pointer",
            color=0xDC333C,
        ))

    @discord.ext.commands.command(name="delete", aliases=["remove"])
    async def delete(self, ctx: DJDiscordContext,
                     indx: IndexConverter) -> typing.Optional[discord.Message]:
        """Deletes a song from the user's playlist"""
        if indx is None:
            return await ctx.send("You need to pick a number bigger than 0")
        playlist = await PlaylistConverter().convert(ctx, str(ctx.author.id))
        if len(playlist.songs) < indx:
            return await ctx.send("No such song exists at index %d" % indx)

        await ctx.send("Removed **`%s`** from your playlist" %
                       playlist.songs[indx - 1]["title"])
        return await playlist.delete_at(ctx, indx)

    @discord.ext.commands.command(name="show", aliases=["list", "queue"])
    async def list(self,
                   ctx: DJDiscordContext,
                   playlist: PlaylistConverter = None
                   ) -> typing.Optional[discord.Message]:
        """Returns a list of songs the user has in his/her playlist"""
        if playlist is None:
            query = await ctx.database.get(author=ctx.author.id)
            if not query:
                return await ctx.send("You haven't created a playlist yet!")
            playlist = Playlist(query["id"], query["songs"], query["author"],
                                query["cover"])
        paginator = discord.ext.menus.MenuPages(
            source=PlaylistPaginator(playlist.songs,
                                     ctx=ctx,
                                     playlist=playlist),
            clear_reactions_after=True,
        )
        await paginator.start(ctx)

    @discord.ext.commands.command(name="add")
    async def add(self, ctx: DJDiscordContext, *,
                  song: SongConverter) -> typing.Optional[discord.Message]:
        """Adds a song to the user's playlist"""
        playlist = await PlaylistConverter().convert(ctx, str(ctx.author.id))
        message = ctx.bot.templates.playlistChange.copy()
        await playlist.add_song(ctx, song)
        return await ctx.send(embed=message.add_field(
            name="New Song!", value="%s {}".format(song.title) % song.emoji))

    @discord.ext.commands.command(name="create", aliases=["new"])
    async def create(
            self, ctx: DJDiscordContext) -> typing.Optional[discord.Message]:
        """Creates a playlist if the user does not already have one, otherwise it will stop execution"""
        if await ctx.database.get(author=ctx.author.id):
            return await ctx.send("You already have a playlist")

        playlist_id = str(uuid.uuid4())
        await ctx.mongodb.djdiscord.playlists.insert_one({
            "id": playlist_id,
            "author": ctx.author.id,
            "songs": [],
            "cover": None,
        })

        msg = await ctx.send(embed=discord.Embed(
            title="Almost there!", color=0xDC333C
        ).add_field(
            name="Cover Art",
            value=
            "Now upload your cover art, if you don't want to upload anything, ignore this message for 20 seconds",
        ).set_image(
            url=
            "https://cdn.discordapp.com/attachments/783142801294098474/800616441169838100/progress.gif"
        ))

        response = await ctx.wait_for(
            "message",
            check=lambda message: message.author == ctx.author,
            timeout=20)

        if response is None:
            return

        if not response.attachments:
            return await ctx.send(
                "You didn't send an attachment to set as your cover art, so we stopped listening"
            )
        await ctx.mongodb.djdiscord.playlists.update_one(
            {"id": playlist_id},
            {"$set": {
                "cover": response.attachments[0].url
            }})

        return await msg.edit(
            embed=discord.Embed(
                title="All done!",
                description=
                "Everything is clear! Begin adding songs to your playlist!",
                color=0xDC333C,
            ).add_field(name="Playlist Code", value=playlist_id)
            # .add_field(name="Song Limit", value="%d" % 40 if ctx.author.premium else 20)
            .set_thumbnail(url=response.attachments[0].url).set_image(
                url=
                "https://cdn.discordapp.com/attachments/783142801294098474/800616839754678272/congrats.gif"
            ))


def setup(bot: discord.ext.commands.Bot) -> None:
    bot.add_cog(Music(bot))
