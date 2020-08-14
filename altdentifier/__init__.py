from .altdentifier import AltDentifier


def setup(bot):
    cog = AltDentifier(bot)
    bot.add_cog(cog)