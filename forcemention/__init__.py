from .forcemention import ForceMention

__red_end_user_data_statement__ = "This cog does not store any End User Data."

def setup(bot):
    bot.add_cog(ForceMention(bot))
