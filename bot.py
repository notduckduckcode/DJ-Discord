import os

import discord
import dotenv

from utils.extensions import DJDiscord

dotenv.load_dotenv()

bot = DJDiscord(
    command_prefix=os.environ["BOT_PREFIX"],
    intents=discord.Intents(
        guild_messages=True,
        voice_states=True,
        guilds=True,
        guild_reactions=True,
        reactions=True,
        typing=True,
    ),
)

bot.run(os.environ["BOT_TOKEN"])
