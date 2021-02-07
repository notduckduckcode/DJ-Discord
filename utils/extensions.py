from __future__ import annotations
import asyncio

import os

import lavalink
import discord
import motor.motor_asyncio
import discord.ext.commands

from pretty_help import PrettyHelp, navigation
from utils.objects import Templates
from utils.database import DJDiscordDatabaseManager


class DJDiscordContext(discord.ext.commands.Context):
    def __init__(self: DJDiscordContext, **kwargs: dict) -> None:
        super().__init__(**kwargs)

    @property
    def mongodb(self: DJDiscordContext) -> motor.motor_asyncio.AsyncIOMotorClient:
        return self.bot.mongo_conn

    @property
    def player(self: DJDiscordContext) -> None:
        if not self.bot.lavalink.player_manager.get(self.guild.id):
            player = self.bot.lavalink.player_manager.create(
                self.guild.id, endpoint=str(self.guild.region)
            )
            return player
        return self.bot.lavalink.player_manager.get(self.guild.id)

    @property
    def voice_queue(self: DJDiscordContext) -> dict:
        return self.bot.voice_queue

    @property
    def database(self: DJDiscordContext) -> DJDiscordDatabaseManager:
        return DJDiscordDatabaseManager(self.bot.mongo_conn)


class DJDiscord(discord.ext.commands.Bot):
    """DJDiscord [discord.ext.commands.Bot] -> Base class for DJ Discord"""

    __version__ = "1.0.0"

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            **kwargs
        )
        self.voice_queue = {}
        self.remove_command("help")
        for object in os.listdir("./commands"):
            if (
                os.path.isfile("./commands/%s" % object)
                and os.path.splitext("./commands/%s" % object)[1] == ".py"
            ):
                self.load_extension("commands.%s" % os.path.splitext(object)[0])
        self.load_extension("jishaku")
        self.loop.create_task(self.update_presence())

    async def update_presence(self) -> None:
        await self.wait_until_ready()
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.competing,
                name="{} server{}. Prefix: dj;".format(
                    len(self.guilds), "" if len(self.guilds) == 1 else "s"
                ),
            )
        )
        await asyncio.sleep(120)

    async def on_connect(self):
        self.lavalink = lavalink.Client(self.user.id)
        self.lavalink.add_node(
            os.environ["LAVALINK_HOST"],
            os.environ["LAVALINK_PORT"],
            os.environ["LAVALINK_PASSWORD"],
            os.environ["LAVALINK_REGION"],
            os.environ["LAVALINK_NODE_NAME"],
        )
        self.add_listener(self.lavalink.voice_update_handler, "on_socket_response")
        self.mongo_conn = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URL"])

    async def on_ready(self):
        print("Ready!")

    async def process_commands(
        self: discord.ext.commands.Bot, message: discord.Message
    ) -> None:
        if message.author.bot:
            return

        ctx = await self.get_context(message, cls=DJDiscordContext)
        await self.invoke(ctx)

    @property
    def templates(self):
        return Templates
