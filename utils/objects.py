from __future__ import annotations  # Py 3.10

import datetime
import typing
from dataclasses import dataclass
from urllib.parse import urlparse

import discord.ext.commands

song_emoji_conversion = {
    "open.spotify.com": "<:spotify:790187623569424424>",
    "soundcloud.com": "<:soundcloud:790187780486987796>",
    "www.youtube.com": "<:youtube:790189633727627294>",
}


class Template(type):
    """Template type"""


class Templates(metaclass=Template):
    eval = discord.Embed(
        title="Evaluation Complete!",
        description=
        "Evaluations are closely monitored for data leaks and as such this message "
        "will self destruct in 10 seconds",
        color=4128651)

    incompleteCmd = discord.Embed(
        title="**`ERROR`** - Insufficent Arguments",
        description=
        "Or in layman's terms, you need to give a bit more for this to work\n```\nUsage:\n{0.bot.command_prefix}{0.command.name} <command> <arguments>\n```"
    )
    cmdError = discord.Embed(
        title="**`ERROR`** - Internal Error",
        description=
        "Or in layman's terms, you may need to tell the developers about this\n```\n{}```"
    ).set_image(url="https://media4.giphy.com/media/TqiwHbFBaZ4ti/giphy.gif")
    playlistChange = discord.Embed(
        title="Done!",
        description="Feel free to share this playlist with your friends!",
        color=0x3EFF8B)
    playlistPaginator = discord.Embed(title="Songs in **`{}`**'s playlist'",
                                      description="Playlist ID: {}",
                                      color=0xE9B44C)
    playlistsPaginator = discord.Embed(title="Songs for `{}`",
                                       description="Total: {} playlists",
                                       color=0xF2DDA4)


@dataclass
class Song:
    source: str
    url: str
    uploader: str
    title: str
    thumbnails: typing.Union[list, str]
    created: typing.Union[datetime.datetime, str]
    length: typing.Union[str, int, datetime.datetime]
    void: bool

    def __getitem__(self, item):
        if isinstance(item, str):
            return getattr(self, item, None)

    @property
    def emoji(self) -> str:
        return song_emoji_conversion[urlparse(self.url).netloc]

    @property
    def json(self) -> dict:
        return {
            "source": self.source,
            "uploader": self.uploader,
            "title": self.title,
            "thumbnails": self.thumbnails,
            "created": self.created,
            "length": self.length,
            "url": self.url,
            "void": self.void
        }


@dataclass
class Station:
    source: str
    thumbnail: typing.Optional[str]
    url: typing.Optional[str]

    @property
    def json(self) -> dict:
        return {"source": self.source, "thumbnail": self.thumbnail, "url": str}

    @staticmethod
    def from_json(_dict: dict) -> Station:
        source = _dict["source"]
        thumbnail = _dict.get("thumbnail")
        url = _dict.get("url")

        return Station(source, thumbnail, url)


class YoutubeLogger(object):
    @staticmethod
    def debug(_):
        """overrides default function, silencing youtube-dl"""
        pass

    @staticmethod
    def warning(_):
        """overrides default function, silencing youtube-dl"""
        pass

    @staticmethod
    def error(_):
        """overrides default function, silencing youtube-dl"""
        pass


ydl_opts = {
    'format':
    'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    "logger":
    YoutubeLogger()
}


class Evaluation:
    pass


class DatabaseEvalResults:
    OK = 0
    WARNING = 1
    ERROR = 2


class LogOpcodes:
    before_command_invoke = 1
    after_command_invoke = 2
    before_cog_invoke = 3
    after_cog_invoke = 4
    error = -1


@dataclass
class DatabaseConfigChange:
    new_val: typing.Optional[dict]
    old_val: typing.Optional[dict]

    @staticmethod
    def from_raw(
            _raw: typing.List[dict]) -> typing.Iterator[DatabaseConfigChange]:
        for change in _raw:
            yield DatabaseConfigChange(change.get("new_val"),
                                       change.get("old_val"))


@dataclass
class DatabaseEvaluation:
    config_changes: typing.Iterator[DatabaseConfigChange]
    dbs_dropped: typing.Optional[int]
    tables_dropped: typing.Optional[int]
    dbs_created: typing.Optional[int]

    @staticmethod
    def from_dict(_dict: dict) -> DatabaseEvaluation:
        dbs_dropped = None
        dbs_created = None
        tables_dropped = None

        raw_config_changes = _dict["config_changes"]

        if _dict.get("dbs_dropped") is not None:
            dbs_dropped = _dict.get("dbs_dropped", 0)

        if _dict.get("dbs_created") is not None:
            dbs_created = _dict.get("dbs_created", 0)

        if _dict.get("tables_dropped") is not None:
            tables_dropped = _dict.get("tables_dropped", 0)

        config_changes = DatabaseConfigChange.from_raw(raw_config_changes)

        return DatabaseEvaluation(config_changes, dbs_dropped, tables_dropped,
                                  dbs_created)


@dataclass
class TableEvaluation:
    opcode: int
    config_changes: typing.Iterator[DatabaseConfigChange]

    @staticmethod
    def from_dict(_dict: dict) -> TableEvaluation:
        if _dict.get("errors"):
            opcode = DatabaseEvalResults.ERROR
        elif _dict.get("warnings"):
            opcode = DatabaseEvalResults.WARNING
        else:
            opcode = DatabaseEvalResults.OK

        raw_config_changes = _dict["config_changes"]

        config_changes = DatabaseConfigChange.from_raw(raw_config_changes)

        return TableEvaluation(opcode, config_changes)


@dataclass
class DocumentEvaluation:
    opcode: int
    errors: typing.Optional[list]
    warnings: typing.Optional[list]
    replaced: int
    inserted: int
    skipped: int
    unchanged: int
    deleted: int

    @staticmethod
    def from_dict(_dict: dict) -> DocumentEvaluation:
        replaced = _dict["replaced"]
        inserted = _dict["inserted"]
        skipped = _dict["skipped"]
        unchanged = _dict["unchanged"]
        deleted = _dict["deleted"]

        errors = None
        warnings = None

        if _errors := _dict.get("errors"):
            opcode = DatabaseEvalResults.ERROR
            errors = _errors
        elif _warnings := _dict.get("warnings"):
            opcode = DatabaseEvalResults.WARNING
            warnings = _warnings
        else:
            opcode = DatabaseEvalResults.OK

        return DocumentEvaluation(opcode, errors, warnings, replaced, inserted,
                                  skipped, unchanged, deleted)


@dataclass
class ErrorOp:
    guild: discord.Guild
    channel: discord.TextChannel
    message: discord.Message
    author: discord.Member

    def __int__(self):
        return LogOpcodes.error

    def __dict__(self):
        return {
            "guild": self.guild.id,
            "channel": self.channel.id,
            "message": self.message.id,
            "author": self.author.id,
            "op": int(self)
        }

    @staticmethod
    def from_context(ctx: discord.ext.commands.Context) -> ErrorOp:
        return ErrorOp(ctx.guild, ctx.channel, ctx.message, ctx.author)


@dataclass
class BeforeCommandInvokeOp:
    executor: discord.Member
    command: discord.ext.commands.Command
    guild: discord.Guild
    channel: discord.TextChannel

    def __int__(self):
        return LogOpcodes.before_command_invoke

    def __dict__(self):
        return {
            "executor": self.executor.id,
            "command": self.command.name,
            "guild": self.guild.id,
            "channel": self.channel.id,
            "op": int(self)
        }

    @staticmethod
    def from_context(
            ctx: discord.ext.commands.Context) -> BeforeCommandInvokeOp:
        return BeforeCommandInvokeOp(ctx.author, ctx.command, ctx.guild,
                                     ctx.channel)


@dataclass
class AfterCommandInvoke:
    executor: discord.Member
    command: discord.ext.commands.Command
    guild: discord.Guild
    channel: discord.TextChannel

    def __int__(self):
        return LogOpcodes.after_command_invoke

    def __dict__(self):
        return {
            "executor": self.executor.id,
            "command": self.command.name,
            "guild": self.guild.id,
            "channel": self.channel.id,
            "op": int(self)
        }


@dataclass
class BeforeCogInvokeOp:
    executor: discord.Member
    cog: discord.ext.commands.Cog
    command: discord.ext.commands.Command
    guild: discord.Guild
    channel: discord.TextChannel

    def __int__(self):
        return LogOpcodes.before_cog_invoke

    def __dict__(self):
        return {
            "executor": self.executor.id,
            "cog": self.cog.name,
            "command": self.command.name,
            "guild": self.guild.id,
            "channel": self.channel.id,
            "op": int(self)
        }

    @staticmethod
    def from_context(ctx: discord.ext.commands.Context) -> BeforeCogInvokeOp:
        return BeforeCogInvokeOp(ctx.author, ctx.cog, ctx.command, ctx.guild,
                                 ctx.channel)


@dataclass
class AfterCogInvokeOp:
    executor: discord.Member
    cog: discord.ext.commands.Cog
    command: discord.ext.commands.Command
    guild: discord.Guild
    channel: discord.TextChannel

    def __int__(self):
        return LogOpcodes.after_cog_invoke

    def __dict__(self):
        return {
            "executor": self.executor.id,
            "cog": self.cog.name,
            "command": self.command.name,
            "guild": self.guild.id,
            "channel": self.channel.id
        }

    @staticmethod
    def from_context(ctx: discord.ext.commands.Context) -> AfterCogInvokeOp:
        return AfterCogInvokeOp(ctx.author, ctx.cog, ctx.command, ctx.guild,
                                ctx.channel)


@dataclass
class Playlist:
    id: int
    songs: list
    author: typing.Union[discord.Member, int, discord.User]
    cover: str

    @staticmethod
    def from_json(_dict: dict) -> Playlist:
        id = _dict["id"]
        songs = _dict["songs"]
        author = _dict["author"]
        cover = _dict["cover"]

        return Playlist(id, songs, author, cover)

    async def delete_at(self, ctx: discord.ext.commands.Context, index: int):
        await ctx.mongodb.djdiscord.playlists.update_one(
            {"id": self.id},
            {"$set": {
                "songs.{}.void".format(index - 1): True
            }})

    async def add_song(self, ctx: discord.ext.commands.Context,
                       song: Song) -> None:
        await ctx.mongodb.djdiscord.playlists.update_one(
            {"id": self.id}, {"$push": {
                "songs": song.json
            }})
