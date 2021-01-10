# Bump restart logic taken from https://github.com/Redjumpman/Jumper-Plugins/tree/V3/raffle
import asyncio
import functools
import logging
from datetime import datetime
from io import BytesIO

import discord
import matplotlib
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

matplotlib.use("agg")
import matplotlib.pyplot as plt

plt.switch_backend("agg")
from collections import Counter

log = logging.getLogger("red.phenom4n4n.disboardreminder")


class DisboardReminder(commands.Cog):
    """
    Set a reminder to bump on Disboard.
    """
    __version__ = "1.1.0"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\nCog Version: {self.__version__}"

    def __init__(self, bot: Red):
        self.bot = bot
        self.load_check = self.bot.loop.create_task(self.bump_worker())
        self.config = Config.get_conf(
            self, identifier=9765573181940385953309, force_registration=True
        )
        default_guild = {
            "channel": None,
            "role": None,
            "message": "It's been 2 hours since the last successful bump, could someone run `!d bump`?",
            "tyMessage": "{member} thank you for bumping! Make sure to leave a review at <https://disboard.org/server/{guild.id}>.",
            "nextBump": None,
            "clean": False,
        }
        default_member = {
            "count": 0,
        }

        self.config.register_member(**default_member)
        self.config.register_guild(**default_guild)

        self.bump_cache = {}
        self.channel_cache = {}
        self.load_check = asyncio.create_task(self.bump_worker())
        self.tasks = []

    def cog_unload(self):
        if self.load_check:
            self.load_check.cancel()
        if self.tasks:
            for task in self.tasks:
                task.cancel()

    async def red_delete_data_for_user(self, requester, user_id):
        for guild, members in await self.config.all_members():
            if user_id in members:
                await self.config.member_from_ids(guild, user_id).clear()

    async def bump_worker(self):
        """Builds channel cache and restarts timers."""
        await self.bot.wait_until_ready()
        for guild_id, guild_data in (await self.config.all_guilds()).items():
            if guild_data["channel"]:
                self.channel_cache[guild_id] = guild_data["channel"]
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
            timer = guild_data["nextBump"]
            if timer:
                now = datetime.utcnow().timestamp()
                remaining = timer - now
                if remaining <= 0:
                    self.tasks.append(asyncio.create_task(self.bump_message(guild)))
                else:
                    self.tasks.append(asyncio.create_task(self.bump_timer(guild, timer)))

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group(aliases=["bprm"])
    async def bumpreminder(self, ctx):
        """Set a reminder to bump on Disboard.

        This sends a reminder to bump in a specified channel 2 hours after someone successfully bumps, thus making it more accurate than a repeating schedule."""

    @bumpreminder.command()
    async def channel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel to send bump reminders to.

        This also works as a toggle, so if no channel is provided, it will disable reminders for this server."""

        if not channel:
            await self.config.guild(ctx.guild).channel.clear()
            await ctx.send("Disabled bump reminders in this server.")
        else:
            try:
                await channel.send(
                    "Set this channel as the reminder channel for bumps. "
                    "I will not send my first reminder until a successful bump is registered."
                )
                await self.config.guild(ctx.guild).channel.set(channel.id)
            except discord.errors.Forbidden:
                await ctx.send("I do not have permission to talk in that channel.")
        await ctx.tick()

    @checks.has_permissions(mention_everyone=True)
    @bumpreminder.command()
    async def pingrole(self, ctx, role: discord.Role = None):
        """Set a role to ping for bump reminders. If no role is provided, it will clear the current role."""

        if not role:
            await self.config.guild(ctx.guild).role.clear()
            await ctx.send("Cleared the role for bump reminders.")
        else:
            await self.config.guild(ctx.guild).role.set(role.id)
            await ctx.send(f"Set {role.name} to ping for bump reminders.")

    @bumpreminder.command(aliases=["ty"])
    async def thankyou(self, ctx, *, message: str = None):
        """Change the message used for 'Thank You' messages. Providing no message will reset to the default message.

        Variables:
        `{member}` - Mentions the user who bumped
        `{guild}` - This server

        Usage: `[p]bprm ty Thanks {member} for bumping! You earned 10 brownie points from phen!`"""

        if message:
            await self.config.guild(ctx.guild).tyMessage.set(message)
            await ctx.tick()
        else:
            await self.config.guild(ctx.guild).tyMessage.clear()
            await ctx.send("Reset this server's Thank You message.")

    @bumpreminder.command()
    async def message(self, ctx, *, message: str = None):
        """Change the message used for reminders. Providing no message will reset to the default message."""

        if message:
            await self.config.guild(ctx.guild).message.set(message)
            await ctx.tick()
        else:
            await self.config.guild(ctx.guild).message.clear()
            await ctx.send("Reset this server's reminder message.")

    @bumpreminder.command()
    async def clean(self, ctx, true_or_false: bool = None):
        """Toggle whether the bot should keep the bump channel "clean."

        The bot will remove all messages in the channel except for bump messages."""

        target_state = (
            true_or_false
            if true_or_false is not None
            else not (await self.config.guild(ctx.guild).clean())
        )
        await self.config.guild(ctx.guild).clean.set(target_state)
        if target_state:
            await ctx.send("I will now clean the bump channel.")
        else:
            await ctx.send("I will no longer clean the bump channel.")

    @bumpreminder.command()
    async def settings(self, ctx):
        """Show your Bump Reminder settings."""
        data = await self.config.guild(ctx.guild).all()

        e = discord.Embed(
            color=await self.bot.get_embed_color(ctx), title="Bump Reminder Settings"
        )
        for key, value in data.items():
            if isinstance(value, str):
                inline = False
                value = f"```{value}```"
            else:
                inline = True
                value = f"`{value}`"
            e.add_field(name=key, value=value, inline=inline)
        if data["nextBump"]:
            timestamp = datetime.fromtimestamp(data["nextBump"])
            e.timestamp = timestamp
            e.set_footer(text="Next bump registered for")
        e.set_author(name=ctx.guild, icon_url=ctx.guild.icon_url)
        await ctx.send(embed=e)

    @commands.guild_only()
    @commands.group(aliases=["bumplb", "bprmtop", "bprmlb"], invoke_without_command=True)
    async def bumpleaderboard(self, ctx, amount: int = 10):
        """View the top Bumpers in the server."""
        if amount < 1:
            raise commands.BadArgument

        members_data = await self.config.all_members(ctx.guild)
        members_list = [(member, data["count"]) for member, data in members_data.items()]
        ordered_list = sorted(members_list, key=lambda m: m[1], reverse=True)[:(amount)]

        mapped_strings = []
        for index, member in enumerate(ordered_list, start=1):
            mapped_strings.append(f"{index}. <@{member[0]}>: {member[1]}")
        if not mapped_strings:
            await ctx.send("There are no tracked bumpers in this server.")
            return

        color = await ctx.embed_color()
        leaderboard_string = "\n".join(mapped_strings)
        if len(leaderboard_string) > 2048:
            embeds = []
            leaderboard_pages = list(pagify(leaderboard_string))
            for index, page in enumerate(leaderboard_pages, start=1):
                embed = discord.Embed(color=color, title="Bump Leaderboard", description=page)
                embed.set_footer(text=f"{index}/{len(leaderboard_pages)}")
                embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
                embeds.append(embed)
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            embed = discord.Embed(
                color=color, title="Bump Leaderboard", description=leaderboard_string
            )
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
            await ctx.send(embed=embed)

    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 15, commands.BucketType.guild)
    @bumpleaderboard.command()
    async def chart(self, ctx: commands.Context):
        """View the top bumpers in a chart."""
        async with ctx.typing():
            counter = Counter()
            members_data = await self.config.all_members(ctx.guild)
            if not members_data:
                await ctx.send("I have no bump data for this server.")
                return

            for member, data in members_data.items():
                _member = ctx.guild.get_member(member)
                if _member:
                    if len(_member.display_name) >= 23:
                        whole_name = "{}...".format(_member.display_name[:20]).replace("$", "\\$")
                    else:
                        whole_name = _member.display_name.replace("$", "\\$")
                    counter[whole_name] = data["count"]
                else:
                    counter[str(member)] = data["count"]

            task = functools.partial(self.create_chart, counter, ctx.guild)
            task = self.bot.loop.run_in_executor(None, task)
            try:
                chart = await asyncio.wait_for(task, timeout=60)
            except asyncio.TimeoutError:
                return await ctx.send(
                    "An error occurred while generating this image. Try again later."
                )
        await ctx.send(file=discord.File(chart, "chart.png"))

    async def bump_timer(self, guild: discord.Guild, remaining: int):
        d = datetime.fromtimestamp(remaining)
        await discord.utils.sleep_until(d)
        await self.bump_message(guild)

    async def bump_message(self, guild: discord.Guild):
        data = await self.config.guild(guild).all()
        channel = guild.get_channel(data["channel"])
        allowed_mentions = discord.AllowedMentions(roles=True)
        if not channel or not channel.permissions_for(guild.me).send_messages:
            await self.config.guild(guild).channel.clear()
        elif data["role"]:
            role = guild.get_role(data["role"])
            if role:
                message = f"{role.mention}: {data['message']}"
                cog = self.bot.get_cog("ForceMention")
                if cog:
                    await cog.forcemention(channel, role, message)
                else:
                    await channel.send(message, allowed_mentions=allowed_mentions)
            else:
                await self.config.guild(guild).role.clear()
        elif channel:
            message = data["message"]
            try:
                await channel.send(message, allowed_mentions=allowed_mentions)
            except discord.errors.Forbidden:
                await self.config.guild(guild).channel.clear()
        else:
            await self.config.guild(guild).channel.clear()
        await self.config.guild(guild).nextBump.clear()

    @commands.Cog.listener("on_message_without_command")
    async def disboard_remind(self, message: discord.Message):
        if not message.guild:
            return

        author: discord.Member = message.author
        channel: discord.TextChannel = message.channel
        guild: discord.Guild = message.guild
        me: discord.Member = guild.me

        bump_chan_id = self.channel_cache.get(guild.id)
        if not bump_chan_id:
            return
        bump_channel = guild.get_channel(bump_chan_id)
        if not bump_channel:
            return

        data = await self.config.guild(guild).all()

        if not data["channel"]:
            return
        clean = data["clean"]
        my_perms = channel.permissions_for(me)

        if (
            clean
            and author != message.guild.me
            and author.id != 302050872383242240
            and channel == bump_channel
        ):
            if my_perms.send_messages:
                await asyncio.sleep(2)
                try:
                    await message.delete()
                except (discord.errors.Forbidden, discord.errors.NotFound):
                    pass

        if not (message.author.id == 302050872383242240 and message.embeds):
            return
        embed = message.embeds[0]
        if "Bump done" in embed.description:
            last_bump = self.bump_cache.get(guild.id) or data["nextBump"]
            if last_bump:
                if not (last_bump - message.created_at.timestamp() <= 0):
                    return
            next_bump = message.created_at.timestamp() + 7200
            self.bump_cache[guild.id] = next_bump
            await self.config.guild(guild).nextBump.set(next_bump)

            words = embed.description.split(",")
            member_mention = words[0]
            member_id = int(member_mention.strip("<@!").rstrip(">"))
            tymessage = data["tyMessage"]
            try:
                await bump_channel.send(
                    tymessage.replace("{member}", member_mention)
                    .replace("{guild}", guild.name)
                    .replace("{guild.id}", str(guild.id))
                )
            except discord.errors.Forbidden:
                pass

            current_count = await self.config.member_from_ids(guild.id, member_id).count()
            current_count += 1
            await self.config.member_from_ids(guild.id, member_id).count.set(current_count)

            await self.bump_timer(message.guild, next_bump)
        else:
            if (
                my_perms.send_messages
                and clean
                and channel == bump_channel
            ):
                await asyncio.sleep(2)
                try:
                    await message.delete()
                except (discord.errors.Forbidden, discord.errors.NotFound):
                    pass

    # original from https://github.com/aikaterna/aikaterna-cogs/tree/v3/chatchart
    def create_chart(self, data: Counter, guild: discord.Guild):
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
        title = plt.title(f"Top Bumpers", color="white")
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
