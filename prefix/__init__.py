from .prefix import Prefix


def setup(bot):
    bot.add_cog(Prefix(bot))