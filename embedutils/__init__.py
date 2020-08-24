from .embed import EmbedUtils


def setup(bot):
    cog = EmbedUtils(bot)
    bot.add_cog(cog)