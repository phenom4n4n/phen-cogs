import discord
from redbot.core import commands
from redbot.core.commands import BadArgument, Converter
from redbot.core.utils.chat_formatting import inline


def hundred_int(arg: str):
    try:
        ret = int(arg)
    except ValueError:
        raise BadArgument(f"{inline(arg)} is not an integer.")
    if ret < 1 or ret > 100:
        raise BadArgument(f"{inline(arg)} must be an integer between 1 and 100.")
    return ret


class Human(commands.MemberConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Member:
        member = await super().convert(ctx, argument)
        if member.bot:
            raise BadArgument("Keep bots out of this. We aren't susceptible to human diseases.")
        return member


class Infectable(Human):
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
        return member


class Curable(Human):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Member:
        member = await super().convert(ctx, argument)
        cog = ctx.bot.get_cog("Plague")
        data = await cog.config.user(member).all()

        if data["gameState"] == "healthy":
            raise BadArgument(f"**{member.name}** is already healthy.")
        elif data["gameRole"] == "Plaguebearer":
            raise BadArgument(f"You cannot cure a Plaguebearer!")
        return member
