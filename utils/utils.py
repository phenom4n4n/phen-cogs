from redbot.core import commands


async def tick(ctx: commands.Context):
    emoji = ctx.bot.get_emoji(729914495459393587) or "\N{WHITE HEAVY CHECK MARK}"
    await ctx.react_quietly(emoji)
