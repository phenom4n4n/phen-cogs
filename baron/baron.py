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

import asyncio
import functools
import time
from io import BytesIO
from typing import List, Literal, Optional, Tuple

import discord
from matplotlib import pyplot as plt
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import GuildConverter, TimedeltaConverter
from redbot.core.config import Config
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import (
    box,
    humanize_list,
    humanize_number,
    humanize_timedelta,
    pagify,
)

from .views import ConfirmationView, PageSource, PaginatedView

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


def comstats_cog(ctx: commands.Context):
    return ctx.bot.get_cog("CommandStats") is not None


def disabled_or_data(data):
    return data or "Disabled"


class Baron(commands.Cog):
    """
    Tools for managing guild joins and leaves.
    """

    __version__ = "1.2.4"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\nCog Version: {self.__version__}"

    default_global = {
        "limit": 0,
        "log_channel": None,
        "log_guild": None,
        "min_members": 0,
        "bot_ratio": 0,
        "whitelist": [],
        "blacklist": [],
    }

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=325236743863625234572,
            force_registration=True,
        )
        self.settings_cache = {}
        self.config.register_global(**self.default_global)

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        return

    async def cog_load(self):
        await self.build_cache()

    async def build_cache(self):
        self.settings_cache = await self.config.all()

    @commands.is_owner()
    @commands.command(aliases=["guildsgrowth", "guildgraph", "guildsgraph"])
    async def guildgrowth(
        self,
        ctx: commands.Context,
        *,
        time: TimedeltaConverter(
            allowed_units=["weeks", "days", "hours"], default_unit="weeks"  # noqa: F821
        ) = None,
    ):
        """
        Show a graph of the bot's guild joins over time.

        Ported from [GuildManager V2](https://github.com/dragdev-studios/guildmanager_v2).
        """
        async with ctx.typing():
            date = ctx.message.created_at - time if time else self.bot.user.created_at
            guilds = [
                guild.me.joined_at
                async for guild in AsyncIter(self.bot.guilds, steps=100)
                if guild.me.joined_at > date
            ]
            if len(guilds) <= 1:
                return await ctx.send("There aren't enough server joins during that time.")

            task = functools.partial(self.create_graph, guilds)
            task = self.bot.loop.run_in_executor(None, task)
            try:
                buf = await asyncio.wait_for(task, timeout=60)
            except asyncio.TimeoutError:
                return await ctx.send(
                    "An error occurred while generating this image. Try again later."
                )
            e = discord.Embed(color=await ctx.embed_color(), title="Guilds Growth")
            e.set_image(url="attachment://attachment.png")
            await ctx.send(embed=e, file=discord.File(buf, "attachment.png"))
            buf.close()

    def create_graph(self, guilds: list):
        plt.clf()
        guilds.sort(key=lambda g: g)
        plt.grid(True)
        fig, ax = plt.subplots()

        ax.plot(guilds, tuple(range(len(guilds))), lw=2)

        fig.autofmt_xdate()

        plt.xlabel("Date")
        plt.ylabel("Guilds")
        buf = BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        return buf

    @commands.is_owner()
    @commands.group()
    async def baron(self, ctx: commands.Context):
        """Baron's watchtower."""

    @baron.command()
    async def settings(self, ctx: commands.Context):
        """View Baron settings."""
        data = await self.config.all()
        log_guild = self.bot.get_guild(data["log_guild"])
        log_chan = data["log_channel"]
        if log_guild and (log_chan := log_guild.get_channel(log_chan)):
            log_chan = log_chan.mention
        description = [
            f"Log Channel: {log_chan}",
            f"Server Limit: {disabled_or_data(data['limit'])}",
            f"Minimum Members: {disabled_or_data(data['min_members'])}",
            f"Bot Farm: {disabled_or_data(data['bot_ratio'])}",
        ]
        e = discord.Embed(
            color=await ctx.embed_color(),
            title="Baron Settings",
            description="\n".join(description),
        )
        await ctx.send(embed=e)

    @baron.command()
    async def limit(self, ctx: commands.Context, limit: int = 0):
        """Set the maximum amount of servers the bot can be in.

        Pass 0 to disable."""
        await self.config.limit.set(limit)
        await ctx.send(
            f"The server limit has been set to {limit}."
            if limit
            else "The server limit has been disabled."
        )
        await self.build_cache()

    @baron.command()
    async def channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set a log channel for Baron alerts."""
        if channel:
            await self.config.log_channel.set(channel.id)
            await self.config.log_guild.set(channel.guild.id)
            await ctx.send(f"Baron's log channel has been set to {channel.mention}.")
        else:
            await self.config.log_channel.clear()
            await self.config.log_guild.clear()
            await ctx.send("Baron's log channel has been removed.")
        await self.build_cache()

    @baron.command(aliases=["wl"])
    async def whitelist(self, ctx: commands.Context, guild_id: int = None):
        """Whitelist a server from Baron actions."""
        if not guild_id:
            e = discord.Embed(
                color=await ctx.embed_color(),
                title="Baron Whitelist",
                description=humanize_list(await self.config.whitelist()),
            )
            await ctx.send(embed=e)
        else:
            if guild_id in await self.config.whitelist():
                await ctx.send("This server is already whitelisted.")
                return
            async with self.config.whitelist() as w:
                w.append(guild_id)
            await ctx.tick()
        await self.build_cache()

    @baron.command(aliases=["unwl"])
    async def unwhitelist(self, ctx: commands.Context, guild_id: int):
        """Remove a server from the whitelist."""
        if guild_id not in await self.config.whitelist():
            await ctx.send("This server is not in the whitelist.")
            return
        async with self.config.whitelist() as w:
            index = w.index(guild_id)
            w.pop(index)
        await ctx.tick()
        await self.build_cache()

    @baron.command(aliases=["bl"])
    async def blacklist(self, ctx: commands.Context, guild_id: int = None):
        """Blacklist the bot from joining a server."""
        if not guild_id:
            e = discord.Embed(
                color=await ctx.embed_color(),
                title="Baron Blacklist",
                description=humanize_list(await self.config.blacklist()),
            )
            await ctx.send(embed=e)
        else:
            if guild_id in await self.config.blacklist():
                await ctx.send("This server is already blacklisted.")
                return
            async with self.config.blacklist() as b:
                b.append(guild_id)
            await ctx.tick()
        await self.build_cache()

    @baron.command(aliases=["unbl"])
    async def unblacklist(self, ctx: commands.Context, guild_id: int):
        """Remove a server from the blacklist."""
        if guild_id not in await self.config.blacklist():
            await ctx.send("This server is not in the blacklist.")
            return
        async with self.config.blacklist() as b:
            index = b.index(guild_id)
            b.pop(index)
        await ctx.tick()
        await self.build_cache()

    @baron.command()
    async def minmembers(self, ctx: commands.Context, limit: Optional[int] = 0):
        """
        Set the minimum number of members a server should have for the bot to stay in it.

        Pass 0 to disable.
        """
        await self.config.min_members.set(limit)
        await ctx.send(
            f"The minimum member limit has been set to {limit}."
            if limit
            else "The minimum member limit has been disabled."
        )
        await self.build_cache()

    @baron.command()
    async def botratio(self, ctx: commands.Context, ratio: Optional[int] = 0):
        """
        Set the bot ratio for servers for the bot to leave.

        Pass 0 to disable.
        """
        if ratio not in range(100):
            raise commands.BadArgument
        await self.config.bot_ratio.set(ratio)
        await ctx.send(
            f"The bot ratio has been set to {ratio}."
            if ratio
            else "The bot ratio has been removed."
        )
        await self.build_cache()

    async def view_guilds(
        self,
        ctx: commands.Context,
        guilds: List[discord.Guild],
        title: str,
        page_length: int = 500,
        *,
        color: discord.Color = discord.Color.red(),
        footer: str = None,
        insert_function=None,
    ):
        page_length = max(100, min(2000, page_length))
        data = await self.config.all()
        whitelist = data["whitelist"]

        desc = []
        async for guild in AsyncIter(guilds, steps=100):
            bots = len([x async for x in AsyncIter(guild.members, steps=100) if x.bot])
            percent = bots / guild.member_count
            guild_desc = [
                f"{guild.name} - ({guild.id})",
                f"Members: **{humanize_number(guild.member_count)}**",
                f"Bots: **{round(percent * 100, 2)}%**",
            ]
            if insert_function:
                guild_desc.append(str(insert_function(guild)))
            if guild.id in whitelist:
                guild_desc.append("[Whitelisted](https://www.youtube.com/watch?v=oHg5SJYRHA0)")
            desc.append("\n".join(guild_desc))

        pages = list(pagify("\n\n".join(desc), ["\n\n"], page_length=page_length))
        embeds = []
        base_embed = discord.Embed(color=color, title=title)
        bot_guilds = self.bot.guilds
        for index, page in enumerate(pages, 1):
            e = base_embed.copy()
            e.description = page
            footer_text = f"{index}/{len(pages)} | {len(guilds)}/{len(bot_guilds)} servers"
            if footer:
                footer_text += f" | {footer}"
            e.set_footer(text=footer_text)
            embeds.append(e)
        source = PageSource(embeds)
        await PaginatedView(source).send_initial_message(ctx)

    @baron.group(name="view")
    async def baron_view(self, ctx: commands.Context):
        """View servers with specific details."""

    @baron_view.command(name="botfarms")
    async def baron_view_botfarms(
        self, ctx: commands.Context, rate: Optional[int] = 75, page_length: Optional[int] = 500
    ):
        """View servers that have a bot to member ratio with the given rate."""
        bot_farms, ok_guilds = await self.get_bot_farms(rate / 100)
        if not bot_farms:
            return await ctx.send(
                f"There are no servers with a bot ratio higher or equal than {rate}%."
            )
        await self.view_guilds(
            ctx, bot_farms, f"Bot Farms ({rate}%)", page_length, footer=f"OK guilds: {ok_guilds}"
        )

    @baron_view.command(name="members")
    async def baron_view_members(
        self,
        ctx: commands.Context,
        members: int,
        less_than: Optional[bool] = True,
        page_length: Optional[int] = 500,
    ):
        """
        View servers that have a member count less than the specified number.

        Pass `False` at the end if you would like to view servers that are greater than the specified number.
        """
        if less_than:
            guilds = [
                guild
                async for guild in AsyncIter(self.bot.guilds, steps=100)
                if guild.member_count < members
            ]
        else:
            guilds = [
                guild
                async for guild in AsyncIter(self.bot.guilds, steps=100)
                if guild.member_count > members
            ]
        if not guilds:
            return await ctx.send(
                f"There are no servers with a member count {'less' if less_than else 'greater'} than {members}."
            )
        await self.view_guilds(ctx, guilds, f"Server Members ({members})", page_length)

    @commands.check(comstats_cog)
    @baron_view.command(name="commands")
    async def baron_view_commands(
        self,
        ctx: commands.Context,
        commands: int,
        highest_first: Optional[bool] = False,
        page_length: Optional[int] = 500,
    ):
        """
        View servers that have command usage less than the specified number.

        Pass `True` at the end if you would like to view servers in order of most commands used.
        """
        cog = self.bot.get_cog("CommandStats")
        data = await cog.config.guilddata()
        guilds = []
        guild_command_usage = {}

        async for guild in AsyncIter(self.bot.guilds, steps=100):
            guild_data = data.get(str(guild.id), {})
            total_commands = sum(guild_data.values())
            if total_commands < commands:
                guilds.append((guild, total_commands))
                guild_command_usage[guild.id] = total_commands
        guilds.sort(key=lambda x: x[1], reverse=highest_first)
        if not guilds:
            return await ctx.send(
                f"There are no servers that have used less than {commands} commands."
            )

        def insert_function(guild: discord.Guild):
            return f"Commands Used: **{guild_command_usage.get(guild.id, 0)}**"

        await self.view_guilds(
            ctx,
            [g async for g, c in AsyncIter(guilds, steps=100)],
            f"Command Usage ({commands})",
            page_length,
            insert_function=insert_function,
        )

    @baron_view.command(name="unchunked")
    async def baron_view_unchunked(
        self,
        ctx: commands.Context,
        page_length: Optional[int] = 500,
    ):
        """View unchunked servers."""
        guilds = [g async for g in AsyncIter(self.bot.guilds, steps=100) if not g.chunked]
        if not guilds:
            return await ctx.send(f"There are no unchunked servers.")

        def insert_function(guild: discord.Guild):
            members = len(guild.members)
            percent = members / guild.member_count
            return f"Members Cached: **{humanize_number(members)} ({round(percent * 100, 2)})%**"

        await self.view_guilds(
            ctx, guilds, "Unchunked Servers", page_length, insert_function=insert_function
        )

    @baron_view.command(name="ownedby")
    async def baron_view_ownedby(
        self, ctx: commands.Context, user: discord.User, page_length: Optional[int] = 500
    ):
        """View servers owned by a user."""
        bot_guilds = self.bot.guilds
        guilds = [g async for g in AsyncIter(bot_guilds, steps=100) if g.owner_id == user.id]
        if not guilds:
            return await ctx.send(f"**{user}** does not own any servers I am in.")

        owned_ratio = len(guilds) / len(bot_guilds)
        await self.view_guilds(
            ctx,
            guilds,
            f"Servers owned by {user}",
            footer=f"{user} owns {round(owned_ratio * 100, 8)}% of the bot's servers",
        )

    @baron.group(name="leave")
    async def baron_leave(self, ctx: commands.Context):
        """Manage leaving servers."""

    @baron_leave.command(name="mass")
    async def baron_leave_mass(
        self,
        ctx: commands.Context,
        guilds: commands.Greedy[GuildConverter],
        *,
        reason: Optional[str] = "I have left this server at the request of my owner.",
    ):
        """Leave servers from a list of IDs."""
        if not guilds:
            raise commands.BadArgument
        await self.leave_guilds(ctx, guilds, reason)

    @baron_leave.command(name="botfarms")
    async def baron_leave_botfarms(
        self, ctx: commands.Context, rate: int = 75, confirm: bool = False
    ):
        """Leave servers with the given bot to member ratio."""
        if rate not in range(1, 100):
            raise commands.BadArgument
        guilds, _ = await self.get_bot_farms(rate / 100)
        if not guilds:
            await ctx.send(f"There are no servers with a bot ratio higher or equal than {rate}%.")
            return
        await self.leave_guilds(
            ctx,
            guilds,
            f"I have automatically left this server since it has a high bot to member ratio.",
            confirmed=confirm,
        )

    @baron_leave.command(name="members")
    async def baron_leave_members(
        self, ctx: commands.Context, members: int, confirm: bool = False
    ):
        """Leave all servers that have less members than the given number."""
        guilds = [
            guild
            async for guild in AsyncIter(self.bot.guilds, steps=100)
            if guild.member_count < members
        ]
        if not guilds:
            await ctx.send(f"There are no servers with a member count less than {members}.")
        await self.leave_guilds(
            ctx,
            guilds,
            f"I have automatically left this server since it has less than {members} members.",
            confirmed=confirm,
        )

    @baron_leave.command(name="blacklisted")
    async def baron_leave_blacklisted(self, ctx: commands.Context, confirm: bool = False):
        """Leave all servers that are blacklisted (in case of downtime)."""
        blacklist = await self.config.blacklist()
        guilds = [g async for g in AsyncIter(self.bot.guilds, steps=100) if g.id in blacklist]
        if not guilds:
            return await ctx.send(f"I'm not in any blacklisted servers.")
        await self.leave_guilds(ctx, guilds, None, notify_guilds=False, confirmed=confirm)

    @commands.check(comstats_cog)
    @baron_leave.command(name="commands")
    async def baron_leave_commands(
        self, ctx: commands.Context, commands: int, confirm: bool = False
    ):
        """Leave all servers that have used less commands than the given number."""
        cog = self.bot.get_cog("CommandStats")
        data = await cog.config.guilddata()
        guilds = []

        async for guild in AsyncIter(self.bot.guilds, steps=100):
            guild_data = data.get(str(guild.id), {})
            total_commands = sum(guild_data.values())
            if total_commands < commands:
                guilds.append(guild)
        if not guilds:
            await ctx.send(
                f"There are no servers with a command usage count less than {commands}."
            )
        await self.leave_guilds(
            ctx,
            guilds,
            f"I have automatically left this server since it has used less than {commands} commands.",
            confirmed=confirm,
        )

    @baron.command(name="chunk")
    async def baron_chunk(self, ctx: commands.Context):
        """
        Chunk unchunked servers.

        Credits to KableKompany
        """
        unchunked = [g async for g in AsyncIter(self.bot.guilds, steps=100) if not g.chunked]
        if not unchunked:
            return await ctx.send("All servers are chunked.")
        await self.chunk(ctx, unchunked)

    async def chunk(self, ctx: commands.Context, guilds: List[discord.Guild]):
        message = await ctx.send(f"Attempting to chunk {len(guilds):,} servers...")
        start = time.perf_counter()
        editing = True
        for index, g in enumerate(guilds, start=1):
            await g.chunk(cache=True)
            if editing and index % 50 == 0 or index == len(guilds):
                try:
                    await message.edit(content=f"{index}/{len(guilds)} servers chunked")
                except discord.HTTPException:
                    editing = False

        end = time.perf_counter()
        seconds = end - start
        await ctx.send(
            f"{ctx.author.mention}, cached {len(guilds):,} servers. Finished in **{humanize_timedelta(seconds=seconds)}**."
        )

    async def leave_guilds(
        self,
        ctx: commands.Context,
        guilds: list,
        message: str,
        *,
        notify_guilds: bool = True,
        confirmed: bool = False,
    ):
        data = await self.config.all()
        unwl_guilds = [
            guild
            async for guild in AsyncIter(guilds, steps=100)
            if guild.id not in data["whitelist"]
        ]
        if not unwl_guilds:
            await ctx.send("There are no servers to leave that aren't whitelisted.")
            return

        name_ids = "\n".join(f"{guild.name} - ({guild.id})" for guild in unwl_guilds[:5])

        guild_preview = name_ids + (
            f"\nand {len(unwl_guilds) - 5} other servers.." if len(unwl_guilds) > 5 else ""
        )

        if not confirmed:
            msg = (
                f"Are you sure you want me to leave the following {len(unwl_guilds)} servers?\n"
                + box(guild_preview, "py")
            )
            if not await ConfirmationView.confirm(ctx, msg):
                return

        async with ctx.typing():
            async for guild in AsyncIter(unwl_guilds, steps=100):
                if notify_guilds:
                    await self.notify_guild(guild, message)
                await guild.leave()
            await self.baron_log("mass_leave", guilds=unwl_guilds, author=ctx.author)
        await ctx.send(f"Done. I left {len(unwl_guilds)} servers.")

    async def get_bot_farms(self, rate: float) -> Tuple[List[discord.Guild], int]:
        bot_farms = []
        ok_guilds = 0
        async for guild in AsyncIter(self.bot.guilds, steps=100):
            bots = len([x async for x in AsyncIter(guild.members, steps=100) if x.bot])
            percent = bots / guild.member_count
            if percent >= rate:
                bot_farms.append(guild)
            else:
                ok_guilds += 1
        return bot_farms, ok_guilds

    async def baron_log(
        self,
        log_type: str,
        *,
        guild: discord.Guild = None,
        guilds: list = None,
        author: discord.User = None,
    ):
        data = self.settings_cache
        if not (data["log_channel"] and data["log_guild"]):
            return
        log_guild = self.bot.get_guild(data["log_guild"])
        if not log_guild:
            return
        channel = log_guild.get_channel(data["log_channel"])
        if not channel or not (
            channel.permissions_for(log_guild.me).send_messages
            and channel.permissions_for(log_guild.me).embed_links
        ):
            return
        if log_type == "limit_leave":
            e = discord.Embed(
                title="Limit Leave",
                description=f"I left {guild.name} since it was past my server limit. ({data['limit']})",
            )
            e.set_author(name=f"{guild} ({guild.id})", icon_url=guild.icon.url)
            await channel.send(embed=e)
        elif log_type == "min_member_leave":
            e = discord.Embed(
                title="Minimum Member Leave",
                description=f"I left {guild.name} since it has less than {data['min_members']} members. ({guild.member_count})",
            )
            e.set_author(name=f"{guild} ({guild.id})", icon_url=guild.icon.url)
            await channel.send(embed=e)
        elif log_type == "mass_leave":
            e = discord.Embed(
                title="Mass Leave",
                description=f"I left {len(guilds)} servers. Requested by {author.mention} - {author}.",
            )
            await channel.send(embed=e)
        elif log_type == "botfarm_leave":
            e = discord.Embed(
                title="Bot Farm Leave",
                description=f"I left {guild.name} since it has a high bot to member ratio. ({data['bot_ratio']}%)",
            )
            e.set_author(name=f"{guild} ({guild.id})", icon_url=guild.icon.url)
            await channel.send(embed=e)
        elif log_type == "bl_leave":
            e = discord.Embed(
                title="Blacklist Leave",
                description=f"I left {guild.name} since it was in the blacklist.",
            )
            e.set_author(name=f"{guild} ({guild.id})", icon_url=guild.icon.url)
            await channel.send(embed=e)

    async def notify_guild(self, guild: discord.Guild, message: str):
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            await guild.system_channel.send(message)
        else:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send(message)
                    break

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        data = self.settings_cache
        if guild.id in data["whitelist"]:
            return
        elif guild.id in data["blacklist"]:
            await guild.leave()
            await self.baron_log("bl_leave", guild=guild)

        if data["limit"] and len(self.bot.guilds) > data["limit"]:
            await self.notify_guild(
                guild,
                f"I have automatically left this server since I am at my server limit. ({data['limit']})",
            )
            await guild.leave()
            await self.baron_log("limit_leave", guild=guild)
            return

        shard_meta = guild.shard_id
        if (
            guild.chunked is False
            and self.bot.intents.members
            and self.bot.shards[shard_meta].is_ws_ratelimited() is False
        ):  # adds coverage for the case where bot is already pulling chunk
            await guild.chunk()
        if data["min_members"] and guild.member_count < data["min_members"]:
            await self.notify_guild(
                guild,
                f"I have automatically left this server since it has less than {data['min_members']} members.",
            )
            await guild.leave()
            await self.baron_log("min_member_leave", guild=guild)
        elif data["bot_ratio"] and (
            len([x async for x in AsyncIter(guild.members, steps=100) if x.bot])
            / guild.member_count
        ) > (data["bot_ratio"] / 100):
            await self.notify_guild(
                guild,
                f"I have automatically left this server since it has a high bot to member ratio.",
            )
            await guild.leave()
            await self.baron_log("botfarm_leave", guild=guild)
