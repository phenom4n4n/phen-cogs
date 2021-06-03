from redbot.core.utils import get_end_user_data_statement

from .connect4 import Connect4

__red_end_user_data_statement__ = get_end_user_data_statement(__file__)


def setup(bot):
    cog = Connect4(bot)
    bot.add_cog(cog)
