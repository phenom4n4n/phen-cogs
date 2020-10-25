
from .webhook import Webhook


def setup(bot):
    bot.add_cog(Webhook(bot))
