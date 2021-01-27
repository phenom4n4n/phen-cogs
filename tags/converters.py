from discord.utils import escape_mentions
from redbot.core import commands
from redbot.core.commands import BadArgument, Converter

from .objects import Tag
from .errors import MissingTagPermissions


class TagName(Converter):
    async def convert(self, ctx: commands.Converter, argument: str) -> str:
        command = ctx.bot.get_command(argument)
        if command:
            raise BadArgument(f"`{argument}` is already a registered command.")
        return "".join(argument.split())


class TagConverter(Converter):
    def __init__(self, *, check_global: bool = False):
        self.check_global = check_global

    async def convert(self, ctx: commands.Context, argument: str) -> Tag:
        if not ctx.guild:
            if not await ctx.bot.is_owner(ctx.author):
                raise BadArgument("Tags may not be used in guilds.")
        cog = ctx.bot.get_cog("Tags")
        tag = cog.get_tag(ctx.guild, argument, self.check_global)
        if tag:
            return tag
        else:
            raise BadArgument(f'Tag "{escape_mentions(argument)}" not found.')


class TagScriptConverter(Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        cog = ctx.bot.get_cog("Tags")
        try:
            await cog.validate_tagscript(ctx, argument)
        except MissingTagPermissions as e:
            raise BadArgument(str(e))
        return argument
