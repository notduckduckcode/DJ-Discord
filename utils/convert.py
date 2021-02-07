import datetime
import re
import textwrap
import typing
from urllib.parse import urlparse
from utils.exceptions import OutOfBoundVolumeError, VolumeTypeError

import lavalink
import discord
import discord.ext.commands
import discord.ext.menus
import discord_argparse
import youtube_dl

from utils.objects import Playlist
from utils.objects import Song
from utils.objects import Station
from utils.objects import song_emoji_conversion
from utils.objects import ydl_opts
from utils.extensions import DJDiscordContext

ArgumentConverter = discord_argparse.ArgumentConverter(
    dj_role=discord_argparse.OptionalArgument(
        discord.Role,
        doc="DJ Role ID that controls voice channel operations.",
        default=None),
    announcement=discord_argparse.OptionalArgument(
        discord.TextChannel,
        doc="Announcement channel ID for DJ Discord announcments",
        default=None))


class IndexConverter(discord.ext.commands.Converter):
    async def convert(self, ctx: DJDiscordContext, argument: str):
        try:
            argument = int(argument)
        except ValueError:
            return

        if argument <= 0:
            return

        return argument


class VolumeConverter(discord.ext.commands.Converter):
    async def convert(self, ctx: DJDiscordContext, argument: str):
        if not argument.isdigit() and not isinstance(argument, int):
            raise VolumeTypeError(int, type(argument))

        if int(argument) < 0 or int(argument) > 200:
            raise OutOfBoundVolumeError(
                "The given volume exceeds the boundary of Lavalink and Discord.py"
            )

        return int(argument)


class StationConverter(discord.ext.commands.Converter):
    async def convert(self, ctx: DJDiscordContext,
                      argument: str) -> typing.Optional[Station]:
        if len(argument) == 4 and re.compile(
                r"[AKNWaknw][a-zA-Z]{0,2}[0123456789][a-zA-Z]{1,3}").match(
                    argument):
            raw = await ctx.database.get(call_sign=argument, table="stations")
            return Station.from_json(raw)

        if re.compile(r'^-?\d+(?:\.\d+)$').match(
                argument) and 87.5 <= float(argument) <= 108:
            if raw := await ctx.database.get(frequency=float(argument),
                                             table="stations"):
                return Station.from_json(raw[0])


class PlaylistConverter(discord.ext.commands.Converter):
    async def convert(self, ctx: DJDiscordContext, argument: str) -> Playlist:
        try:
            author = await discord.ext.commands.MemberConverter().convert(
                ctx, argument)
            playlist = await ctx.database.get(author=author.id)
            return Playlist.from_json(playlist)
        except Exception as exc:
            if isinstance(exc, discord.ext.commands.MemberNotFound):
                return

        if (re.compile(
                "^[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$"
        ).match(argument) is not None):
            playlist = await ctx.mongodb.djdiscord.playlists.find_one(
                {"id": argument})
            return Playlist(playlist["id"], playlist["songs"],
                            playlist["author"], playlist["cover"])

        slot = await ctx.database.get(author=ctx.author.id)
        return Playlist(slot["id"], slot["songs"], slot["author"],
                        slot["cover"])

class SongConverter(discord.ext.commands.Converter):
    async def convert(self, ctx: DJDiscordContext, argument: str) -> Song:
        target = "ytsearch:%s" % argument

        if urlparse(argument).netloc in (
                "open.spotify.com",
                "www.youtube.com",
                "soundcloud.com",
        ):
            target = argument

        with youtube_dl.YoutubeDL(ydl_opts) as ytdl:
            if data := ytdl.extract_info(target, download=False):
                if "entries" in data and data.get("entries"):
                    return Song(
                        data["entries"][0]["formats"][0]["url"],
                        data["entries"][0]["webpage_url"],
                        data["entries"][0]["uploader"],
                        data["entries"][0]["title"],
                        data["entries"][0]["thumbnails"],
                        datetime.datetime.strptime(
                            data["entries"][0]["upload_date"],
                            "%Y%m%d").astimezone().strftime("%Y-%m-%d"),
                        data["entries"][0]["duration"], False)

                return Song(
                    data["formats"][0]["url"], data["webpage_url"],
                    data["uploader"], data["title"], data["thumbnails"],
                    datetime.datetime.strptime(
                        data["upload_date"],
                        "%Y%m%d").astimezone().strftime("%Y-%m-%d"),
                    data["duration"], False)

            return None


class PlaylistPaginator(discord.ext.menus.ListPageSource):
    def __init__(self,
                 entries: typing.List[str],
                 *,
                 playlist: Playlist,
                 ctx: DJDiscordContext,
                 per_page: int = 4):
        super().__init__(entries, per_page=per_page)
        self.templates = ctx.bot.templates
        self.playlist = playlist
        self.author = ctx.author

    async def format_page(self, menu, page: typing.List[str]) -> discord.Embed:
        offset = menu.current_page * self.per_page

        template = self.templates.playlistPaginator.copy()
        template.title = template.title.format(str(self.author))
        template.description = template.description.format(self.playlist.id)

        if self.playlist.cover:
            template.set_thumbnail(url=self.playlist.cover)

        if not page:
            template.add_field(
                name="Take this lemon \U0001f34b",
                value="You have no songs in your playlist, go add some!")

        for index, song in enumerate(page, start=offset):
            if not song["void"]:
                template.add_field(
                    name="%s `{}.` {}".format(index + 1, song["title"]) %
                    song_emoji_conversion[urlparse(song["url"]).netloc],
                    value=
                    "Created: `{0[created]}`\nDuration: `{0[length]}` seconds, Author: `{0[uploader]}`"
                    .format(song),
                    inline=False)

        return template


class NameValidator(discord.ext.commands.Converter):
    async def convert(
        self: discord.ext.commands.Converter,
        _: DJDiscordContext,
        argument: str,
    ):
        # if ctx.author.premium: no premium yet :p
        # return textwrap.shorten(argument, 40)
        return textwrap.shorten(argument, 20)

class PlaylistsPaginator(discord.ext.menus.ListPageSource):
    def __init__(self, *, ctx: DJDiscordContext, playlists: typing.List[dict]):
        super().__init__(playlists, per_page=1)
        self.author = ctx.author
        self.templates = ctx.bot.templates
        self.playlists = playlists

    async def format_page(self, menu, page):
        format = self.templates.playlistsPaginator.copy()
        format.title = format.title.format(self.author.name)
        format.description = format.description.format(len(self.playlists))
        format.add_field(name="`%s`" % page["name"],
                         value="ID: `{0[id]}`, Song Count: `{1}`".format(
                             page, len(page["songs"])))
        return format
