import typing
from uuid import UUID
import traceback
import discord
import discord.ext.commands
import json


class CustomEmbed(discord.Embed):
    def _fill(
        self,
        ctx: discord.ext.commands.Context,
        id: typing.Optional[UUID] = None,
        error: typing.Optional[typing.Union[
            discord.ext.commands.CommandInvokeError, Exception]] = None
    ) -> discord.Embed:
        _traceback = None

        if error := getattr(error, "original", error):
            _traceback = "".join(
                traceback.TracebackException.from_exception(
                    error).format()).strip()

        self.title, self.description = self.title.format(
            ctx, id, _traceback), self.description.format(ctx, id, _traceback)

        for field in self._fields:
            field["name"] = field.get("name").format(ctx, id, _traceback)

        return self


class InsuffArgs(CustomEmbed):
    def __new__(cls, *args, **kwargs) -> None:
        with open("./assets/insuff_args.json") as file:
            return CustomEmbed.from_dict(json.load(file))._fill(*args, **kwargs)


class RuntimeErr(CustomEmbed):
    def __new__(cls, *args, **kwargs) -> None:
        with open("./assets/runtime_err.json") as file:
            return CustomEmbed.from_dict(json.load(file))._fill(*args, **kwargs)
