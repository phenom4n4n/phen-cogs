"""
MIT License

Copyright (c) 2020-2021 phenom4n4n

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

import random
from datetime import date
from typing import Literal, Optional

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class Ratings(commands.Cog):
    """
    Rate how simp you are.
    """

    __version__ = "1.0.0"

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=2353262345234652,
            force_registration=True,
        )

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        return

    @commands.command()
    async def simprate(
        self, ctx: commands.Context, member: Optional[discord.Member], *, simpable: Optional[str]
    ):
        """Find out how much someone is simping for something."""
        member = member or ctx.author
        rate = random.choice(range(1, 100))
        emoji = self.bot.get_emoji(758821832169619467) or "😳"
        if simpable:
            message = f"{member.mention} is **{rate}**% simping for {simpable} {emoji}"
        else:
            message = f"{member.mention} is **{rate}**% simp {emoji}"
        await ctx.send(message, allowed_mentions=discord.AllowedMentions(users=False))

    @commands.command()
    async def clownrate(self, ctx: commands.Context, member: Optional[discord.Member]):
        """Reveal someone's clownery."""
        member = member or ctx.author
        rate = random.choice(range(1, 100))
        emoji = self.bot.get_emoji(758821900808880138) or "🤡"
        message = f"{member.mention} is **{rate}**% clown {emoji}"
        await ctx.send(message, allowed_mentions=discord.AllowedMentions(users=False))

    @commands.command(aliases=["iq"])
    async def iqrate(self, ctx: commands.Context, member: Optional[discord.Member]):
        """100% legit IQ test."""
        member = member or ctx.author
        random.seed(member.id + self.bot.user.id)
        if await self.bot.is_owner(member):
            iq = random.randint(200, 500)
        else:
            iq = random.randint(-10, 200)
        if iq >= 160:
            emoji = self.bot.get_emoji(758821860972036106) or "🧠"
        elif iq >= 100:
            emoji = self.bot.get_emoji(758821993768026142) or "🤯"
        else:
            emoji = self.bot.get_emoji(758821971319586838) or "😔"
        await ctx.send(
            f"{member.mention} has an IQ of {iq} {emoji}",
            allowed_mentions=discord.AllowedMentions(users=False),
        )

    @commands.command(aliases=["sanity"])
    async def sanitycheck(self, ctx: commands.Context, member: Optional[discord.Member]):
        """Check your sanity."""
        member = member or ctx.author
        random.seed(str(member.id) + str(date.today().strftime("%j")) + str(self.bot.user.id))
        sanity = random.randint(0, 100)
        await ctx.send(
            f"{member.mention} is {sanity}% sane today.",
            allowed_mentions=discord.AllowedMentions(users=False),
        )
