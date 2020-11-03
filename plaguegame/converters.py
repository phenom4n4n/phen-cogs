import discord
from redbot.core import commands
from redbot.core.commands import BadArgument, Converter, MemberConverter
from redbot.core.utils.chat_formatting import inline
from unidecode import unidecode
from rapidfuzz import process


def hundred_int(arg: str):
    try:
        ret = int(arg)
    except ValueError:
        raise BadArgument(f"{inline(arg)} is not an integer.")
    if ret < 1 or ret > 100:
        raise BadArgument(f"{inline(arg)} must be an integer between 1 and 100.")
    return ret


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


class FuzzyHuman(FuzzyMember):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Member:
        member = await super().convert(ctx, argument)
        if member.bot:
            raise BadArgument("Keep bots out of this. We aren't susceptible to human diseases.")
        return member


class Infectable(FuzzyHuman):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Member:
        member = await super().convert(ctx, argument)
        cog = ctx.bot.get_cog("Plague")
        data = await cog.config.user(member).all()
        game_data = await cog.config.all()

        if data["gameState"] == "infected":
            raise BadArgument(
                f"**{member.name}** is already infected with {game_data['plagueName']}."
            )
        elif data["gameRole"] == "Doctor":
            raise BadArgument(f"You cannot infect a Doctor!")
        elif data["gameRole"] == "God":
            raise BadArgument(f"Don't mess with God.")
        return member


class Curable(FuzzyHuman):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Member:
        member = await super().convert(ctx, argument)
        cog = ctx.bot.get_cog("Plague")
        data = await cog.config.user(member).all()

        if data["gameState"] == "healthy":
            raise BadArgument(f"**{member.name}** is already healthy.")
        elif data["gameRole"] == "Plaguebearer":
            raise BadArgument(f"You cannot cure a Plaguebearer!")
        elif data["gameRole"] == "God":
            raise BadArgument(f"Don't mess with God.")
        return member
