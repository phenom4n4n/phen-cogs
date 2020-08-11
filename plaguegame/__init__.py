from .plague import Plague


def setup(bot):
    bot.add_cog(Plague(bot))