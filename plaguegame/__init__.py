from .plague import Plague

__red_end_user_data_statement__ = "This cog stores data on users based off their interactions within the game. Examples of such data are their 'health state' (healthy or infected) or their 'game role' (user, doctor, plaguebearer)."


def setup(bot):
    bot.add_cog(Plague(bot))
