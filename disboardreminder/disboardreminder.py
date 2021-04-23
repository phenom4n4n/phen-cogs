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
import re
from collections import defaultdict
from datetime import datetime
from typing import Coroutine, Optional

import discord
import TagScriptEngine as tse
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.utils import AsyncIter

from .converters import FuzzyRole, StrictRole

log = logging.getLogger("red.phenom4n4n.disboardreminder")

DISBOARD_BOT_ID = 302050872383242240
LOCK_REASON = "DisboardReminder auto-lock"
MENTION_RE = re.compile(r"<@!?(\d{15,20})>")


class DisboardReminder(commands.Cog):
    """
    Set a reminder to bump on Disboard.
    """

    __version__ = "1.3.0"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\nCog Version: {self.__version__}"

    default_guild_cache = {"channel": None, "tasks": {}}

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=9765573181940385953309, force_registration=True
        )
        default_guild = {
            "channel": None,
            "role": None,
            "message": "It's been 2 hours since the last successful bump, could someone run `!d bump`?",
            "tyMessage": "{member(mention)} thank you for bumping! Make sure to leave a review at <https://disboard.org/server/{guild(id)}>.",
            "nextBump": None,
            "lock": False,
            "clean": False,
        }
        self.config.register_guild(**default_guild)

        self.channel_cache = {}
        self.bump_loop = self.create_task(self.bump_check_loop())
        self.bump_tasks = defaultdict(dict)
        # self.cache = defaultdict(lambda _: self.default_guild_cache.copy())
        bot.add_dev_env_value("bprm", lambda _: self)

        blocks = [
            tse.LooseVariableGetterBlock(),
            tse.AssignmentBlock(),
            tse.IfBlock(),
            tse.EmbedBlock(),
        ]
        self.tagscript_engine = tse.Interpreter(blocks)

    def cog_unload(self):
        self.bot.remove_dev_env_value("bprm")
        if self.bump_loop:
            self.bump_loop.cancel()
        for tasks in self.bump_tasks.values():
            for task in tasks.values():
                task.cancel()

    def task_done_callback(self, task: asyncio.Task):
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as error:
            log.exception(f"Task failed.", exc_info=error)

    def create_task(self, coroutine: Coroutine, *, name: str = None):
        task = asyncio.create_task(coroutine, name=name)
        task.add_done_callback(self.task_done_callback)
        return task

    async def initialize(self):
        async for guild_id, guild_data in AsyncIter(
            (await self.config.all_guilds()).items(), steps=100
        ):
            if guild_data["channel"]:
                self.channel_cache[guild_id] = guild_data["channel"]

    async def red_delete_data_for_user(self, requester, user_id):
        for guild, members in await self.config.all_members():
            if user_id in members:
                await self.config.member_from_ids(guild, user_id).clear()

    async def bump_check_loop(self):
        await self.bot.wait_until_ready()
        while True:
            try:
                await self.bump_check_guilds()
            except Exception as error:
                log.exception("An exception occured in the bump restart loop.", exc_info=error)
            await asyncio.sleep(60)

    async def bump_check_guilds(self):
        async for guild_id, guild_data in AsyncIter(
            (await self.config.all_guilds()).items(), steps=100
        ):
            if not (guild := self.bot.get_guild(guild_id)):
                continue
            await self.bump_check_guild(guild, guild_data)

    async def bump_check_guild(self, guild: discord.Guild, guild_data: dict):
        # task logic taken from redbot.cogs.mutes
        end_time = guild_data["nextBump"]
        if not end_time:
            return
        now = datetime.utcnow().timestamp()
        remaining = end_time - now
        if remaining > 60:
            return

        if remaining <= 0:
            task_name = f"bump_remind:{guild.id}-{end_time}"
            if task_name in self.bump_tasks[guild.id]:
                return
            task = self.create_task(self.bump_remind(guild), name=task_name)
        else:
            task_name = f"bump_timer:{guild.id}-{end_time}"
            if task_name in self.bump_tasks[guild.id]:
                return
            task = self.create_task(self.bump_timer(guild, end_time), name=task_name)

        self.bump_tasks[guild.id][task_name] = task
        await asyncio.sleep(0.2)

    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group(aliases=["bprm"])
    async def bumpreminder(self, ctx):
        """
        Set a reminder to bump on Disboard.

        This sends a reminder to bump in a specified channel 2 hours after someone successfully bumps, thus making it more accurate than a repeating schedule.
        """

    @bumpreminder.command(name="channel")
    async def bumpreminder_channel(self, ctx, channel: discord.TextChannel = None):
        """
        Set the channel to send bump reminders to.

        This also works as a toggle, so if no channel is provided, it will disable reminders for this server.
        """
        if not channel and ctx.guild.id in self.channel_cache:
            del self.channel_cache[ctx.guild.id]
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
    @bumpreminder.command(name="pingrole")
    async def bumpreminder_pingrole(self, ctx: commands.Context, role: FuzzyRole = None):
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

    @bumpreminder.command(name="thankyou", aliases=["ty"])
    async def bumpreminder_thankyou(self, ctx, *, message: str = None):
        """
        Change the message used for 'Thank You' messages. Providing no message will reset to the default message.

        The thank you message supports TagScript blocks which can customize the message and even add an embed!
        [View the TagScript documentation here.](https://phen-cogs.readthedocs.io/en/latest/index.html)

        Variables:
        `{member}` - [The user who bumped](https://phen-cogs.readthedocs.io/en/latest/default_variables.html#author-block)
        `{server}` - [This server](https://phen-cogs.readthedocs.io/en/latest/default_variables.html#server-block)

        Blocks:
        `embed` - [Embed to be sent in the thank you message](https://phen-cogs.readthedocs.io/en/latest/parsing_blocks.html#embed-block)

        **Examples:**
        > `[p]bprm ty Thanks {member} for bumping! You earned 10 brownie points from phen!`
        > `[p]bprm ty {embed(description):{member(mention)}, thank you for bumping! Make sure to vote for **{server}** on [our voting page](https://disboard.org/server/{guild(id)}).}
        """
        if message:
            await self.config.guild(ctx.guild).tyMessage.set(message)
            await ctx.tick()
        else:
            await self.config.guild(ctx.guild).tyMessage.clear()
            await ctx.send("Reset this server's Thank You message.")

    @bumpreminder.command(name="message")
    async def bumpreminder_message(self, ctx, *, message: str = None):
        """Change the message used for reminders. Providing no message will reset to the default message."""
        if message:
            await self.config.guild(ctx.guild).message.set(message)
            await ctx.tick()
        else:
            await self.config.guild(ctx.guild).message.clear()
            await ctx.send("Reset this server's reminder message.")

    @bumpreminder.command(name="clean")
    async def bumpreminder_clean(self, ctx, true_or_false: bool = None):
        """
        Toggle whether [botname] should keep the bump channel "clean."

        [botname] will remove all failed invoke messages by Disboard.
        """
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
    @bumpreminder.command(name="lock")
    async def bumpreminder_lock(self, ctx, true_or_false: bool = None):
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

    @bumpreminder.command(name="settings")
    async def bumpreminder_settings(self, ctx: commands.Context):
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

        description = [
            f"**Channel:** {channel}",
            f"**Ping Role:** {pingrole}",
            f"**Auto-lock:** {data['lock']}",
            f"**Clean Mode:** {data['clean']}",
        ]
        description = "\n".join(description)

        e = discord.Embed(
            color=await ctx.embed_color(),
            title="Bump Reminder Settings",
            description=description,
        )
        e.set_author(name=ctx.guild, icon_url=ctx.guild.icon_url)

        for key, value in data.items():
            if isinstance(value, str):
                value = f"```{discord.utils.escape_markdown(value)}```"
                e.add_field(name=key, value=value, inline=False)
        if data["nextBump"]:
            timestamp = datetime.fromtimestamp(data["nextBump"])
            e.timestamp = timestamp
            e.set_footer(text="Next bump registered for")
        await ctx.send(embed=e)

    async def bump_timer(self, guild: discord.Guild, timestamp: int):
        d = datetime.fromtimestamp(timestamp)
        await discord.utils.sleep_until(d)
        await self.bump_remind(guild)

    @staticmethod
    async def set_my_permissions(
        guild: discord.Guild, channel: discord.TextChannel, my_perms: discord.Permissions
    ):
        if not my_perms.send_messages:
            my_perms.update(send_messages=True)
            await channel.set_permissions(guild.me, overwrite=my_perms, reason=LOCK_REASON)

    async def autolock_channel(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        my_perms: discord.Permissions,
        *,
        lock,
    ):
        await self.set_my_permissions(guild, channel, my_perms)

        current_perms = channel.overwrites_for(guild.default_role)
        check = False if lock else None
        if current_perms.send_messages is not check:
            current_perms.update(send_messages=check)
            await channel.set_permissions(
                guild.default_role,
                overwrite=current_perms,
                reason=LOCK_REASON,
            )

    async def bump_remind(self, guild: discord.Guild):
        guild = self.bot.get_guild(guild.id)
        if not guild:
            return
        data = await self.config.guild(guild).all()
        channel = guild.get_channel(data["channel"])

        if not channel:
            await self.config.guild(guild).channel.clear()
            return
        my_perms = channel.permissions_for(guild.me)
        if not my_perms.send_messages:
            await self.config.guild(guild).channel.clear()
            return

        if data["lock"] and my_perms.manage_roles:
            await self.autolock_channel(guild, channel, my_perms, lock=False)

        message = data["message"]
        allowed_mentions = self.bot.allowed_mentions
        if data["role"]:
            role = guild.get_role(data["role"])
            if role:
                message = f"{role.mention}: {message}"
                allowed_mentions = discord.AllowedMentions(roles=[role])

        kwargs = self.process_tagscript(message)
        try:
            await channel.send(allowed_mentions=allowed_mentions, **kwargs)
        except discord.Forbidden:
            await self.config.guild(guild).channel.clear()
        await self.config.guild(guild).nextBump.clear()

    def validate_cache(self, message: discord.Message) -> Optional[discord.TextChannel]:
        guild: discord.Guild = message.guild
        if not guild:
            return
        if message.author.id != DISBOARD_BOT_ID:
            return
        bump_chan_id = self.channel_cache.get(guild.id)
        if not bump_chan_id:
            return
        return guild.get_channel(bump_chan_id)

    def validate_success(self, message: discord.Message) -> Optional[discord.Embed]:
        if not message.embeds:
            return
        embed = message.embeds[0]
        if "Bump done" in embed.description:
            return embed

    async def respond_to_bump(
        self,
        data: dict,
        bump_channel: discord.TextChannel,
        message: discord.Message,
        embed: discord.Embed,
    ):
        guild: discord.Guild = message.guild
        my_perms = bump_channel.permissions_for(guild.me)
        next_bump = message.created_at.timestamp() + 7200
        await self.config.guild(guild).nextBump.set(next_bump)

        match = MENTION_RE.search(embed.description)
        if match:
            member_id = int(match.group(1))
            if not guild.chunked:
                await guild.chunk()
            user = guild.get_member(member_id) or await self.bot.get_or_fetch(member_id)
            member_adapter = tse.MemberAdapter(user)
        else:
            member_adapter = tse.StringAdapter("Unknown User")
        tymessage = data["tyMessage"]

        if my_perms.send_messages:
            guild_adapter = tse.GuildAdapter(guild)
            seed = {"member": member_adapter, "guild": guild_adapter, "server": guild_adapter}
            kwargs = self.process_tagscript(tymessage, seed_variables=seed)
            await bump_channel.send(**kwargs)
        else:
            await self.config.guild(guild).channel.clear()

        if data["lock"] and my_perms.manage_roles:
            await self.autolock_channel(guild, bump_channel, my_perms, lock=True)

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        bump_channel = self.validate_cache(message)
        if not bump_channel:
            return

        guild: discord.Guild = message.guild
        channel: discord.TextChannel = message.channel

        data = await self.config.guild(guild).all()
        if not data["channel"]:
            return
        clean = data["clean"]
        my_perms = channel.permissions_for(guild.me)

        if embed := self.validate_success(message):
            last_bump = data["nextBump"]
            if last_bump and not (last_bump - message.created_at.timestamp() <= 0):
                return
            await self.respond_to_bump(data, bump_channel, message, embed)
        else:
            if my_perms.manage_messages and clean and channel == bump_channel:
                await asyncio.sleep(2)
                try:
                    await message.delete()
                except (discord.Forbidden, discord.NotFound):
                    pass

    def process_tagscript(self, content: str, *, seed_variables: dict = {}):
        output = self.engine.process(content, seed_variables)
        kwargs = {}
        if output.body:
            kwargs["content"] = output.body[:2000]
        if embed := output.actions.get("embed"):
            kwargs["embed"] = embed
        return kwargs
