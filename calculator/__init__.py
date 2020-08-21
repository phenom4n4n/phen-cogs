from .calculator import Calculator


def setup(bot):
    cog = Calculator(bot)
    bot.add_cog(cog)