import typing
import uuid

import discord
import discord.ext.commands

from utils.embeds import insuff_args
from utils.converters import VoicePrompt, VolumeConverter
from utils.constants import BeforeCogInvokeOp, AfterCogInvokeOp, ErrorOp
from utils.converters import StationConverter
from utils.extensions import DJDiscordContext
from utils.voice import VoiceState


class RadioCog(discord.ext.commands.Cog):
    async def cog_before_invoke(self, ctx: DJDiscordContext) -> None:
        await ctx.database.log(
            BeforeCogInvokeOp(ctx.author, self, ctx.command, ctx.guild,
                              ctx.channel), )
        await ctx.trigger_typing()

    async def cog_after_invoke(self, ctx: DJDiscordContext) -> None:
        await ctx.database.log(
            AfterCogInvokeOp(ctx.author, self, ctx.command, ctx.guild,
                             ctx.channel), )

    async def cog_command_error(self, ctx: DJDiscordContext, error: Exception) -> None:
        _id = uuid.uuid4()
        await ctx.database.log(
            ErrorOp(ctx.guild, ctx.channel, ctx.message, ctx.author),
            error=error,
            case_id=_id
        )
        print(f"An error occurred during command runtime. Case ID: {_id}")

    @discord.ext.commands.group(name="radio")
    async def radio(self, ctx: discord.ext.commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            return await ctx.send(embed=insuff_args)

    @radio.command()
    async def start(
        self,
        ctx: discord.ext.commands.Context,
        station: StationConverter,
        channel: discord.VoiceChannel = None
    ) -> typing.Optional[discord.Message]:
        # insert...
        if ctx.author.voice is None:
            return await ctx.send(
                "You need to be connected to a channel in order to start playing music"
            )

        if station is None:
            return await ctx.send(
                "You have not specified a valid radio station to start playing"
            )

        if channel is None:
            channel = ctx.author.voice.channel

        target = channel if channel is not None else ctx.author.voice.channel

        state = ctx.voice_queue.get(ctx.guild.id)
        if not state:
            state = VoiceState(ctx.bot, ctx, station)
            ctx.voice_queue[ctx.guild.id] = state

        ctx.voice_state = state

        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(target)
            return

        state.voice = await target.connect()

        def handle_after(error) -> None:
            if error:
                raise error

            ctx.bot.loop.create_task(state.stop())
            ctx.bot.loop.create_task(ctx.send("Debug #1"))

        ctx.voice_queue[ctx.guild.id].voice.play(
            discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(
                station.source),
                                         volume=1),
            after=handle_after,
        )

    @radio.command(name="stop", aliases=["end", "interrupt", "sigint"])
    async def stop(self,
                   ctx: DJDiscordContext) -> typing.Optional[discord.Message]:
        if ctx.author.voice is None:
            return await ctx.send(
                "You need to be connected to a channel in order to stop music")

        state = ctx.voice_queue.get(ctx.guild.id)

        if len(state.voice.channel.members) <= 3:
            await ctx.send(embed=discord.Embed(
                title="Disconnected from the voice channel and stopped playing",
                color=0xA1D2CE,
            ))
            return await state.stop()

        if len(state.voice.channel.members) >= 3 and await ctx.dj:
            vote_count = await VoicePrompt("Stop the current song?").prompt(ctx
                                                                            )
            if vote_count >= 1:
                await state.stop()

    @radio.command
    async def volume(self, ctx: DJDiscordContext,
                     volume: VolumeConverter) -> None:
        if ctx.author.voice is None:
            return await ctx.send(
                "You need to be connected to a channel in order to change the volume"
            )

        state = ctx.voice_queue.get(ctx.guild.id)

        state.voice.source.volume = volume

    @radio.command
    async def info(self, ctx: discord.ext.commands.Context) -> None:
        # insert...
        pass


def setup(bot: discord.ext.commands.Bot) -> None:
    bot.add_cog(RadioCog())
