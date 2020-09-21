import discord
import asyncio
import time
from TagScriptEngine import block, Interpreter, adapter

from redbot.core import commands, checks


class Calculator(commands.Cog):
    """
    Do math
    """

    def __init__(self, bot):
        self.bot = bot
        blocks = [
            block.MathBlock(),
            block.RandomBlock(),
            block.RangeBlock(),
        ]
        self.engine = Interpreter(blocks)

    async def red_delete_data_for_user(self, **kwargs):
        return

    @commands.command(aliases=["calc"])
    async def calculate(self, ctx, *, query):
        """Math"""
        engine_input = "{m:" + query + "}"
        start = time.monotonic()
        output = self.engine.process(engine_input)
        end = time.monotonic()

        output_string = output.body.replace("{m:", "").replace("}", "")
        e = discord.Embed(
            color=await ctx.embed_color(),
            title=f"Input: `{query}`",
            description=f"Output: `{output_string}`",
        )
        e.set_footer(text=f"Calculated in {round((end - start) * 1000, 3)} ms")
        await ctx.send(embed=e)
