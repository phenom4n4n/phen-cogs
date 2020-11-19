from typing import Literal
import matplotlib
import re
from io import BytesIO

matplotlib.use("agg")
import functools
import asyncio
import matplotlib.pyplot as plt

plt.switch_backend("agg")
from collections import Counter
import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

ID_RE = re.compile(r"\d{15,21}")


class BanChart(commands.Cog):
    """
    Display a chart of the moderators with the most bans.
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=283457823853246562378,
            force_registration=True,
        )

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        return

    @commands.cooldown(1, 300, commands.BucketType.guild)
    @commands.max_concurrency(10, commands.BucketType.default)
    @commands.mod_or_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True, view_audit_log=True)
    @commands.command()
    async def banchart(self, ctx: commands.Context, limit: int = 5000):
        """Display a chart of the moderators with the most bans.

        This can take a while for servers with lots of bans."""
        await ctx.trigger_typing()
        ban_count = len(await ctx.guild.bans())
        if not ban_count:
            return await ctx.send("This server has no bans.")
        limit = min(10000, min(limit, ban_count))
        await ctx.send(f"Gathering stats for the last {limit} bans.")
        await ctx.trigger_typing()
        counter = Counter()
        async for entry in ctx.guild.audit_logs(action=discord.AuditLogAction.ban, limit=limit):
            if entry.user.bot and entry.reason:
                match = re.search(ID_RE, entry.reason)
                if match:
                    mod_id = int(match.group(0))
                    user = self.bot.get_user(mod_id) or mod_id
                else:
                    user = entry.user
            else:
                user = entry.user
            name = str(user)
            if len(name) > 23:
                name = name[:20] + "..."
            counter[name] += 1
        task = functools.partial(self.create_chart, counter, f"Ban Mods for the last {limit} bans")
        task = self.bot.loop.run_in_executor(None, task)
        try:
            banchart = await asyncio.wait_for(task, timeout=60)
        except asyncio.TimeoutError:
            return await ctx.send(
                "An error occurred while generating this image. Try again later."
            )
        await ctx.send(file=discord.File(banchart, "banchart.png"))

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
            others = sum([x[1] / total for x in most_common[20:]])
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
