from redbot.core import commands

try:
    from redbot.core.core_commands import MAX_PREFIX_LENGTH
except ImportError:
    MAX_PREFIX_LENGTH = 20


class PrefixConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        if len(argument) > MAX_PREFIX_LENGTH and not await ctx.bot.is_owner(ctx.author):
            raise commands.BadArgument(f"Prefixes cannot be above {MAX_PREFIX_LENGTH} in length.")
        return argument
