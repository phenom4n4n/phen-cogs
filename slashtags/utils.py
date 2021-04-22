from redbot.core import commands


def dev_check(ctx: commands.Context):
    return ctx.bot.get_cog("Dev")
