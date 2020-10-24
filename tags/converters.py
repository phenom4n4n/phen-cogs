from discord.utils import escape_mentions
from redbot.core import commands
from redbot.core.commands import BadArgument, Converter

from .objects import Tag


class TagName(Converter):
    async def convert(self, ctx: commands.Converter, argument: str) -> str:
        command = ctx.bot.get_command(argument)
        if command:
            raise BadArgument(f"`{argument}` is already a registered command.")
        return "".join(argument.split())


class TagConverter(Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> Tag:
        cog = ctx.bot.get_cog("Tags")
        tags = await cog.config.guild(ctx.guild).tags()
        tag = tags.get(argument)
        if tag:
            tag = Tag.from_dict(argument, tag, ctx=ctx)
            return tag
        else:
            raise BadArgument(f'Tag "{escape_mentions(argument)}" not found.')
