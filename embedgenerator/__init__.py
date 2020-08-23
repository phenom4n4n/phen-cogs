from .embed import EmbedGenerator


def setup(bot):
    cog = EmbedGenerator(bot)
    bot.add_cog(cog)