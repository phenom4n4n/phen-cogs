from .allowedmentions import AllowedMentions


def setup(bot):
    bot.add_cog(AllowedMentions(bot))
