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

import re
from io import BytesIO
from typing import Tuple, Union

import matplotlib

matplotlib.use("agg")
import asyncio
import functools

import matplotlib.pyplot as plt

plt.switch_backend("agg")
from collections import Counter

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

ID_RE = re.compile(r"\d{15,21}")
LIMIT = 10000


class BanChart(commands.Cog):
    """
    Display a chart of the moderators with the most bans.
    """

    __version__ = "1.1.0"

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=283457823853246562378,
            force_registration=True,
        )

    async def red_delete_data_for_user(self, *, requester: str, user_id: int) -> None:
        return

    @staticmethod
    async def get_ban_limit(ctx: commands.Context, limit: int) -> Tuple[int, list]:
        await ctx.trigger_typing()
        bans = ctx.guild.bans()
        ban_count = len(bans)
        if not ban_count:
            raise commands.UserFeedbackCheckFailure("This server has no bans.")
        limit = min(LIMIT, min(limit, ban_count))
        await ctx.send(f"Gathering stats up to the last {limit} bans.")
        return limit, bans

    @staticmethod
    def get_name(user: Union[discord.User, int]) -> str:
        name = str(user)
        if len(name) > 23:
            name = name[:20] + "..."
        return name.replace("$", "\\$")

    async def get_chart_file(self, ctx: commands.Context, counter: Counter) -> discord.File:
        task = functools.partial(
            self.create_chart, counter, f"Ban Mods for the last {sum(counter.values())} bans"
        )
        task = self.bot.loop.run_in_executor(None, task)
        try:
            banchart = await asyncio.wait_for(task, timeout=60)
        except asyncio.TimeoutError:
            return await ctx.send(
                "An error occurred while generating this image. Try again later."
            )
        return discord.File(banchart, "banchart.png")

    @commands.cooldown(1, 300, commands.BucketType.guild)
    @commands.max_concurrency(10, commands.BucketType.default)
    @commands.mod_or_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True, view_audit_log=True)
    @commands.group(invoke_without_command=True)
    async def banchart(self, ctx: commands.Context, limit: int = LIMIT):
        """
        Display a chart of the moderators with the most bans.

        This can take a while for servers with lots of bans.
        """
        limit, _ = await self.get_ban_limit(ctx, limit)
        async with ctx.typing():
            counter = Counter()
            async for entry in ctx.guild.audit_logs(
                action=discord.AuditLogAction.ban, limit=limit
            ):
                if entry.user.bot and entry.reason:
                    match = ID_RE.search(entry.reason)
                    if match:
                        mod_id = int(match.group(0))
                        user = self.bot.get_user(mod_id) or mod_id
                    else:
                        user = entry.user
                else:
                    user = entry.user
                counter[self.get_name(user)] += 1
            chart_file = await self.get_chart_file(ctx, counter)
        await ctx.send(file=chart_file)

    @banchart.command("storedbans")
    async def banchart_storedbans(self, ctx: commands.Context, limit: int = LIMIT):
        """
        Creates a ban chart using the server's bans rather than audit logs.
        """
        _, bans = await self.get_ban_limit(ctx, limit)
        async with ctx.typing():
            counter = Counter()
            for ban in bans:
                if ban.reason and (match := ID_RE.search(ban.reason)):
                    mod_id = int(match.group(0))
                    user = self.bot.get_user(mod_id) or mod_id
                    counter[self.get_name(user)] += 1
            chart_file = await self.get_chart_file(ctx, counter)
        await ctx.send(file=chart_file)

    # original from https://github.com/aikaterna/aikaterna-cogs/
    def create_chart(self, data: Counter, title: str):
        plt.clf()
        most_common = data.most_common()
        total = sum(data.values())
        sizes = [(x[1] / total) * 100 for x in most_common][:20]
        labels = [
            f"{x[0]} {round(sizes[index], 1):g}%" for index, x in enumerate(most_common[:20])
        ]
        if len(most_common) > 20:
            others = sum(x[1] / total for x in most_common[20:])
            sizes.append(others)
            labels.append("Others {:g}%".format(others))
        title = plt.title(title, color="white")
        title.set_va("top")
        title.set_ha("center")
        plt.gca().axis("equal")
        colors = [
            "r",
            "darkorange",
            "gold",
            "y",
            "olivedrab",
            "green",
            "darkcyan",
            "mediumblue",
            "darkblue",
            "blueviolet",
            "indigo",
            "orchid",
            "mediumvioletred",
            "crimson",
            "chocolate",
            "yellow",
            "limegreen",
            "forestgreen",
            "dodgerblue",
            "slateblue",
            "gray",
        ]
        pie = plt.pie(sizes, colors=colors, startangle=0)
        plt.legend(
            pie[0],
            labels,
            bbox_to_anchor=(0.7, 0.5),
            loc="center",
            fontsize=10,
            bbox_transform=plt.gcf().transFigure,
            facecolor="#ffffff",
        )
        plt.subplots_adjust(left=0.0, bottom=0.1, right=0.45)
        image_object = BytesIO()
        plt.savefig(image_object, format="PNG", facecolor="#36393E")
        image_object.seek(0)
        return image_object
