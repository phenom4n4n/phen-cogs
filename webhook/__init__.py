import json
from pathlib import Path

from .webhook import Webhook


def setup(bot):
    bot.add_cog(Webhook(bot))
