from .disboardreminder import DisboardReminder


def setup(bot):
    bot.add_cog(DisboardReminder(bot))