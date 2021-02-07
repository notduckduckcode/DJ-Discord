import typing
from utils.extensions import DJDiscordContext
import discord.ext.commands
import discord


def form_syntax(command: discord.ext.commands.command):
    cmd_and_aliases = " | ".join([str(command), *command.aliases])
    params = []

    for key, value in command.params.items():
        if key not in ("self", "ctx"):
            params.append(f"[{key}]" if "NoneType" in
                          str(value) else f"<{key}>")

    params = " ".join(params)

    return f"**Usage:** `w/{cmd_and_aliases} {params}`"


@discord.ext.commands.command(name="help",
                              aliases=["helpme", "bonjour", "hi", "hello"])
async def help(ctx: DJDiscordContext, command: typing.Optional[str]):
    if not command:
        embed = discord.Embed(
            title="djdiscord v{0.__version__} help embed".format(ctx.bot))
        embed.add_field(
            name="Voice \U0001f399 / Music \U0001f3b5",
            value="`dj;add`, `dj;create`, `dj;delete`, `dj;loop`, "
            "`dj;now`, `dj;radiostart`, `dj;play`, `dj;radiostart`, "
            "`dj;rawplay`, `dj;show`, `dj;skip`, `dj;stop`, `dj;volume`",
            inline=False)
        embed.add_field(name="Informational commands \U0001f4d8",
                        value="`dj;info`",
                        inline=False)
        return await ctx.send(embed=embed)

    if func_command := discord.utils.get(ctx.bot.commands, name=command):
        embed = discord.Embed(
            title="djdiscord v{0.__version__} help for the command {1}".format(
                ctx.bot, command))
        embed.add_field(name="Usage", value=form_syntax(func_command))
        embed.add_field(name="Description",
                        value=func_command.__doc__ if func_command.__doc__ else
                        "No description was provided for this command.")
        return await ctx.send(embed=embed)

    return await ctx.send(
        "An invalid command was given, please check your spelling and try again."
    )


def setup(bot: discord.ext.commands.Bot):
    bot.add_command(help)
