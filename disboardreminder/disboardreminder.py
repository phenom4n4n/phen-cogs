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

from collections import Counter

log = logging.getLogger("red.phenom4n4n.disboardreminder")


class DisboardReminder(commands.Cog):
    """
    Set a reminder to bump on Disboard.
    """

    __version__ = "1.1.1"

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
            if my_perms.send_messages and clean and channel == bump_channel:
                await asyncio.sleep(2)
                try:
                    await message.delete()
                except (discord.errors.Forbidden, discord.errors.NotFound):
                    pass
