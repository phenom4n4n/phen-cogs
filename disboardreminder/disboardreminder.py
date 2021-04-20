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

# Bump restart logic taken from https://github.com/Redjumpman/Jumper-Plugins/tree/V3/raffle
import asyncio
import logging
from collections import Counter, defaultdict
from datetime import datetime
from typing import Optional

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils.predicates import MessagePredicate

log = logging.getLogger("red.phenom4n4n.disboardreminder")

from .converters import FuzzyRole, StrictRole


class DisboardReminder(commands.Cog):
    """
    Set a reminder to bump on Disboard.
    """

    __version__ = "1.2.1"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\nCog Version: {self.__version__}"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=9765573181940385953309, force_registration=True
        )
        default_guild = {
            "channel": None,
            "role": None,
            "reward_role": None,
            "message": "It's been 2 hours since the last successful bump, could someone run `!d bump`?",
            "tyMessage": "{member} thank you for bumping! Make sure to leave a review at <https://disboard.org/server/{guild.id}>.",
            "nextBump": None,
            "lock": False,
            "clean": False,
            "weekly": Counter(),
        }
        default_member = {
            "count": 0,
        }

        self.config.register_member(**default_member)
        self.config.register_guild(**default_guild)

        self.bump_cache = {}
        self.channel_cache = {}
        self.load_check = asyncio.create_task(self.bump_worker())
        self.tasks = defaultdict(list)

    def cog_unload(self):
        if self.load_check:
            self.load_check.cancel()
        if self.tasks:
            for guild_id, task_list in self.tasks.items():
                for task in task_list:
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
                    self.tasks[guild.id].append(asyncio.create_task(self.bump_message(guild)))
                else:
                    self.tasks[guild.id].append(asyncio.create_task(self.bump_timer(guild, timer)))
                await asyncio.sleep(0.2)

    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group(aliases=["bprm"])
    async def bumpreminder(self, ctx):
        """Set a reminder to bump on Disboard.

        This sends a reminder to bump in a specified channel 2 hours after someone successfully bumps, thus making it more accurate than a repeating schedule."""

    @bumpreminder.command()
    async def channel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel to send bump reminders to.

        This also works as a toggle, so if no channel is provided, it will disable reminders for this server."""
        if not channel and self.channel_cache.get(ctx.guild.id):
            await self.config.guild(ctx.guild).channel.clear()
            await ctx.send("Disabled bump reminders in this server.")
        elif channel:
            try:
                await channel.send(
                    "Set this channel as the reminder channel for bumps. "
                    "I will not send my first reminder until a successful bump is registered."
                )
            except discord.errors.Forbidden:
                await ctx.send("I do not have permission to talk in that channel.")
            else:
                await self.config.guild(ctx.guild).channel.set(channel.id)
                self.channel_cache[ctx.guild.id] = channel.id
        else:
            raise commands.BadArgument

    @commands.has_permissions(mention_everyone=True)
    @bumpreminder.command()
    async def pingrole(self, ctx: commands.Context, role: FuzzyRole = None):
        """
        Set a role to ping for bump reminders.

        If no role is provided, it will clear the current role.
        """
        if not role:
            await self.config.guild(ctx.guild).role.clear()
            await ctx.send("Cleared the role for bump reminders.")
        else:
            await self.config.guild(ctx.guild).role.set(role.id)
            await ctx.send(f"Set {role.name} to ping for bump reminders.")

    # @commands.is_owner()
    # @commands.has_permissions(manage_roles=True)
    # @bumpreminder.command(name="rewardrole")
    async def bumpreminder_rewardrole(self, ctx: commands.Context, role: StrictRole = None):
        """
        Set a reward role to give to the top bumper.

        If no role is provided, it will clear the current role.
        """
        if not role:
            await self.config.guild(ctx.guild).reward_role.clear()
            await ctx.send("Cleared the bump reward role.")
        else:
            await self.config.guild(ctx.guild).reward_role.set(role.id)
            await ctx.send(f"Set {role.name} as the bump reward role.")
            await self.assign_reward_role(ctx.guild, role)

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
        """Toggle whether [botname] should keep the bump channel "clean."

        [botname] will remove all failed invoke messages by Disboard."""
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

    @commands.has_permissions(manage_roles=True)
    @bumpreminder.command()
    async def lock(self, ctx, true_or_false: bool = None):
        """Toggle whether the bot should automatically lock/unlock the bump channel."""
        target_state = (
            true_or_false
            if true_or_false is not None
            else not (await self.config.guild(ctx.guild).lock())
        )
        await self.config.guild(ctx.guild).lock.set(target_state)
        if target_state:
            await ctx.send("I will now auto-lock the bump channel.")
        else:
            await ctx.send("I will no longer auto-lock the bump channel.")

    @commands.is_owner()
    @bumpreminder.command(hidden=True)
    async def resetweekly(self, ctx: commands.Context):
        """Reset the weekly bump leaderboard."""
        pred = MessagePredicate.yes_or_no(ctx=ctx)
        await ctx.send("Are you sure you want to reset the weekly bump leaderboard?")
        try:
            await self.bot.wait_for("message", check=pred, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send(
                "Confirmation timed out, not resetting the weekly bump leaderboard.."
            )
        if pred.result is True:
            await self.config.guild(ctx.guild).weekly.clear()
            await ctx.send(f"Weekly bump leaderboard reset.")
        else:
            await ctx.send(f"Alright, not resetting the weekly bump leaderboard..")

    @bumpreminder.command()
    async def settings(self, ctx):
        """Show your Bump Reminder settings."""
        data = await self.config.guild(ctx.guild).all()
        guild = ctx.guild

        if channel := guild.get_channel(data["channel"]):
            channel = channel.mention
        else:
            channel = "None"
        if pingrole := guild.get_role(data["role"]):
            pingrole = pingrole.mention
        else:
            pingrole = "None"
        if reward_role := guild.get_role(data["reward_role"]):
            reward_role = reward_role.mention
        else:
            reward_role = "None"
        description = [
            f"**Channel:** {channel}",
            f"**Ping Role:** {pingrole}",
            # f"**Reward Role:** {reward_role}",
            f"**Auto-lock:** {data['lock']}",
            f"**Clean Mode:** {data['clean']}",
        ]
        description = "\n".join(description)

        e = discord.Embed(
            color=await self.bot.get_embed_color(ctx),
            title="Bump Reminder Settings",
            description=description,
        )
        for key, value in data.items():
            if isinstance(value, str):
                value = f"```{discord.utils.escape_markdown(value)}```"
                e.add_field(name=key, value=value, inline=False)
        if data["nextBump"]:
            timestamp = datetime.fromtimestamp(data["nextBump"])
            e.timestamp = timestamp
            e.set_footer(text="Next bump registered for")
        e.set_author(name=ctx.guild, icon_url=ctx.guild.icon_url)
        await ctx.send(embed=e)

    @commands.is_owner()
    @commands.guild_only()
    @commands.group(
        aliases=["bumplb", "bprmtop", "bprmlb"], invoke_without_command=True, hidden=True
    )
    async def bumpleaderboard(self, ctx, amount: int = 10):
        """View the top Bumpers in the server."""
        if amount < 1:
            raise commands.BadArgument

        members_data = await self.config.all_members(ctx.guild)
        members_list = [(member, data["count"]) for member, data in members_data.items()]
        ordered_list = sorted(members_list, key=lambda m: m[1], reverse=True)[:(amount)]

        mapped_strings = [
            f"{index}. <@{member[0]}>: {member[1]}"
            for index, member in enumerate(ordered_list, start=1)
        ]

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

    @bumpleaderboard.command(name="weekly")
    async def bumpleaderboard_weekly(self, ctx: commands.Context, amount: int = 10):
        """View the top Bumpers in the server."""
        if amount < 1:
            raise commands.BadArgument

        members_data = await self.config.guild(ctx.guild).weekly()
        members_list = [(member, count) for member, count in members_data.most_common()]
        members_list.sort(key=lambda m: m[1], reverse=True)

        mapped_strings = [
            f"{index}. <@{member_id}>: {member_count}"
            for index, (member_id, member_count) in enumerate(members_list, start=1)
        ]

        if not mapped_strings:
            await ctx.send("There are no tracked weekly bumpers in this server.")
            return

        color = await ctx.embed_color()
        leaderboard_string = "\n".join(mapped_strings)
        if len(leaderboard_string) > 2048:
            embeds = []
            leaderboard_pages = list(pagify(leaderboard_string))
            for index, page in enumerate(leaderboard_pages, start=1):
                embed = discord.Embed(
                    color=color, title="Weekly Bump Leaderboard", description=page
                )
                embed.set_footer(text=f"{index}/{len(leaderboard_pages)}")
                embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
                embeds.append(embed)
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            embed = discord.Embed(
                color=color, title="Weekly Bump Leaderboard", description=leaderboard_string
            )
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
            await ctx.send(embed=embed)

    async def bump_timer(self, guild: discord.Guild, remaining: int):
        d = datetime.fromtimestamp(remaining)
        await discord.utils.sleep_until(d)
        await self.bump_message(guild)

    async def bump_message(self, guild: discord.Guild):
        guild = self.bot.get_guild(guild.id)
        if not guild:
            return
        data = await self.config.guild(guild).all()
        channel = guild.get_channel(data["channel"])

        if not channel or not channel.permissions_for(guild.me).send_messages:
            await self.config.guild(guild).channel.clear()
            return

        my_perms = channel.permissions_for(guild.me)
        if data["lock"] and my_perms.manage_roles:
            if my_perms.send_messages is not True:
                my_perms.update(send_messages=True)
                await channel.set_permissions(
                    guild.me, overwrite=my_perms, reason="DisboardReminder auto-lock"
                )

            current_perms = channel.overwrites_for(guild.default_role)
            if current_perms.send_messages is not None:
                current_perms.update(send_messages=None)
                await channel.set_permissions(
                    guild.default_role,
                    overwrite=current_perms,
                    reason="DisboardReminder auto-lock",
                )

        if data["role"]:
            role = guild.get_role(data["role"])
            if role:
                message = f"{role.mention}: {data['message']}"
                await self.bot.get_cog("ForceMention").forcemention(channel, role, message)
            else:
                await self.config.guild(guild).role.clear()
        else:
            message = data["message"]
            mentionPerms = discord.AllowedMentions(roles=True)
            try:
                await channel.send(message, allowed_mentions=mentionPerms)
            except discord.errors.Forbidden:
                await self.config.guild(guild).channel.clear()
        await self.config.guild(guild).nextBump.clear()

    async def get_top_bumper(self, guild: discord.Guild) -> Optional[discord.Member]:
        members_data = await self.config.all_members(guild)
        members_list = []
        if not guild.chunked:
            await guild.chunk()
        for member, data in members_data.items():
            if member := guild.get_member(member):
                members_list.append((member, data["count"]))
        if members_list:
            members_list.sort(key=lambda m: m[1], reverse=True)
            return members_list[0][0]

    async def assign_reward_role(self, guild: discord.Guild, role: discord.Role):
        if role.position >= guild.me.top_role.position:
            await self.config.guild(guild).reward_role.clear()
            return
        member = await self.get_top_bumper(guild)
        if not member:
            return
        if role.members:
            for m in role.members:
                if m != member:
                    await m.remove_roles(role, reason="Not the top bumper")
        if role.id not in [r.id for r in member.roles]:
            await member.add_roles(role, reason="Top bumper")

    @commands.Cog.listener("on_message_without_command")
    async def disboard_remind(self, message: discord.Message):
        if not message.guild:
            return

        author: discord.Member = message.author
        channel: discord.TextChannel = message.channel
        guild: discord.Guild = message.guild
        me: discord.Member = guild.me

        if author.id != 302050872383242240:
            return
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
            and author.id != guild.me.id
            and author.id != 302050872383242240
            and channel.id == bump_channel.id
        ) and my_perms.manage_messages:
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
            if last_bump and not (last_bump - message.created_at.timestamp() <= 0):
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
            except discord.Forbidden:
                pass

            current_count = await self.config.member_from_ids(guild.id, member_id).count()
            current_count += 1
            await self.config.member_from_ids(guild.id, member_id).count.set(current_count)
            weekly_counter = data["weekly"]
            weekly_counter[str(member_id)] += 1
            await self.config.guild(guild).weekly.set(weekly_counter)

            if data["lock"] and my_perms.manage_roles:
                if my_perms.send_messages is not True:
                    my_perms.update(send_messages=True)
                    await bump_channel.set_permissions(
                        me, overwrite=my_perms, reason="DisboardReminder auto-lock"
                    )

                current_perms = bump_channel.overwrites_for(guild.default_role)
                if current_perms.send_messages is not False:
                    current_perms.update(send_messages=False)
                    await bump_channel.set_permissions(
                        guild.default_role,
                        overwrite=current_perms,
                        reason="DisboardReminder auto-lock",
                    )

            # if reward_role := guild.get_role(data["reward_role"]):
            #    await self.assign_reward_role(guild, reward_role)

            self.tasks[guild.id].append(
                asyncio.create_task(self.bump_timer(message.guild, next_bump))
            )
        else:
            if my_perms.manage_messages and clean and channel.id == bump_channel.id:
                await asyncio.sleep(2)
                try:
                    await message.delete()
                except (discord.errors.Forbidden, discord.errors.NotFound):
                    pass
