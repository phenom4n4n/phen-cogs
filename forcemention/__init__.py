from .forcemention import ForceMention


def setup(bot):
    bot.add_cog(ForceMention(bot))
