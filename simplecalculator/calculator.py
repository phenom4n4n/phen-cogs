"""
MIT License

Copyright (c) 2020-present phenom4n4n

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import time

import discord
from redbot.core import commands
from TagScriptEngine import Interpreter, block


class Calculator(commands.Cog):
    """
    Do math
    """

    __version__ = "1.0.1"

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
    async def calculate(self, ctx: commands.Context, *, query):
        """
        Calculate a math expression.

        **Example:**
        `[p]calculate 7 / (2 * 2)`
        """
        query = query.replace(",", "")
        engine_input = "{m:" + query + "}"
        start = time.monotonic()
        output = self.engine.process(engine_input)
        end = time.monotonic()

        output_string = output.body.replace("{m:", "").replace("}", "")
        try:
            fmt_str = f"{float(output_string):,}"
        except ValueError:
            fmt_str = output_string
        e = discord.Embed(
            color=await ctx.embed_color(),
            title=f"Input: `{query[:247]}`",
            description=f"Output: `{fmt_str}`",
        )
        e.set_footer(text=f"Calculated in {round((end - start) * 1000, 3)} ms")
        await ctx.send(embed=e)
