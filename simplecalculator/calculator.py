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

        self.calculator.run('3 * 10')
        await ctx.send(self.calculator.log)