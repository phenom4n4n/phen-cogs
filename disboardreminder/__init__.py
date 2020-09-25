from .disboardreminder import DisboardReminder

__red_end_user_data_statement__ = "This cog stores the number of times a member has bumped."


def setup(bot):
    bot.add_cog(DisboardReminder(bot))
