import discord
from redbot.core import commands
from redbot.core.commands import BadArgument, MemberConverter
from unidecode import unidecode
from rapidfuzz import process


# original converter from https://github.com/TrustyJAID/Trusty-cogs/blob/master/serverstats/converters.py#L19
class FuzzyMember(MemberConverter):
    def __init__(self, response: bool = True):
        self.response = response
        super().__init__()

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        try:
            member = await super().convert(ctx, argument)
        except BadArgument:
            guild = ctx.guild
            result = []
            for m in process.extract(
                argument,
                {m: unidecode(m.name) for m in guild.members},
                limit=None,
                score_cutoff=75,
            ):
                result.append((m[2], m[1]))

            if not result:
                raise BadArgument(f'Member "{argument}" not found.' if self.response else None)

            sorted_result = sorted(result, key=lambda r: r[1], reverse=True)
            member = sorted_result[0][0]
        return member
