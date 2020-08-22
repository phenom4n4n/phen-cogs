import discord
import asyncio
from calculator.simple import SimpleCalculator

from redbot.core import commands, checks

class Calculator(commands.Cog):
    """
    Do math
    """

    def __init__(self, bot):
        self.bot = bot
        self.calculator = SimpleCalculator()

    @commands.command(aliases=["calc"])
    async def calculate(self, ctx, *, query):
        """Math"""
        query = query.strip()
        query = query.replace(",", "")
        self.calculator.run(query)
        result_dict = {}
        for item in self.calculator.log:
            item = item.split(": ")
            if len(item) >= 2:
                result_dict.update({item[0]:item[1]})
        try:
            query = result_dict["input string"]
            result = result_dict["result"]
        except KeyError:
            return await ctx.send("Invalid math operation")
        result_embed = discord.Embed(
            title=query,
            description=result
        )
        await ctx.send(embed=result_embed)