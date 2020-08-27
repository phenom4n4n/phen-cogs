from .linkquoter import LinkQuoter


def setup(bot):
    cog = LinkQuoter(bot)
    bot.add_cog(cog)