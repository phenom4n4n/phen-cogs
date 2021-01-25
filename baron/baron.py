import asyncio
from typing import Literal, Optional, List
from matplotlib import pyplot as plt
from io import BytesIO
import functools
import time

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import GuildConverter, TimedeltaConverter
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import box, humanize_list, pagify, humanize_timedelta, humanize_number
from redbot.core.utils.menus import DEFAULT_CONTROLS, close_menu, menu, start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


def comstats_cog(ctx: commands.Context):
    return ctx.bot.get_cog("CommandStats") is not None


def disabled_or_data(data):
    return data if data else "Disabled"


class Baron(commands.Cog):
    """
    Tools for managing guild joins and leaves.
    """
    __version__ = "1.1.0"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\nCog Version: {self.__version__}"

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=325236743863625234572,
            force_registration=True,
        )
        default_global = {
            "limit": 0,
            "log_channel": None,
            "log_guild": None,
            "min_members": 0,
            "bot_ratio": 0,
            "whitelist": [],
            "blacklist": [],
        }
        self.config.register_global(**default_global)

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        return

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
        await ctx.trigger_typing()
        if time:
            date = ctx.message.created_at - time
        else:
            date = self.bot.user.created_at
        guilds = [
            guild.me.joined_at
            for guild in self.bot.guilds
            if guild.me.joined_at.timestamp() > date.timestamp()
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
        log_chan = data["log_channel"]
        if log_chan := self.bot.get_channel(data["log_channel"]):
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

    @baron.command()
    async def botratio(self, ctx: commands.Context, ratio: Optional[int] = 0):
        """
        Set the bot ratio for servers for the bot to leave.

        Pass 0 to disable.
        """
        if ratio not in range(0, 100):
            raise commands.BadArgument
        await self.config.bot_ratio.set(ratio)
        await ctx.send(
            f"The bot ratio has been set to {ratio}."
            if ratio
            else "The bot ratio has been removed."
        )

    async def view_guilds(
        self,
        ctx: commands.Context,
        guilds: List[discord.Guild],
        title: str,
        page_length: int = 500,
        *,
        command_count: Optional[int] = None,
        color: discord.Color = discord.Color.red(),
        footer: str = None,
        insert_function = None
    ):
        page_length = max(100, min(2000, page_length))
        data = await self.config.all()
        whitelist = data["whitelist"]

        desc = []
        for guild in guilds:
            bots = len([x for x in guild.members if x.bot])
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
        for index, page in enumerate(pages, 1):
            e = base_embed.copy()
            e.description = page
            footer_text = f"{index}/{len(pages)}"
            if footer:
                footer_text += f" | {footer}"
            e.set_footer(text=footer_text)
            embeds.append(e)
        await menu(ctx, embeds, DEFAULT_CONTROLS)

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
            return await ctx.send(f"There are no servers with a bot ratio higher or equal than {rate}%.")
        await self.view_guilds(ctx, bot_farms, f"Bot Farms ({rate}%)", page_length, footer=f"OK guilds: {ok_guilds}")

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
            guilds = [guild for guild in self.bot.guilds if guild.member_count < members]
        else:
            guilds = [guild for guild in self.bot.guilds if guild.member_count > members]
        if not guilds:
            return await ctx.send(f"There are no servers with a member count {'less' if less_than else 'greater'} than {members}.")
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

        for guild in self.bot.guilds:
            guild_data = data.get(str(guild.id), {})
            total_commands = sum(guild_data.values())
            if total_commands < commands:
                guilds.append((guild, total_commands))
                guild_command_usage[guild.id] = total_commands
        guilds.sort(key=lambda x: x[1], reverse=highest_first)
        if not guilds:
            return await ctx.send(f"There are no servers that have used less than {commands} commands.")

        def insert_function(guild: discord.Guild):
            return f"Commands Used: **{guild_command_usage.get(guild.id, 0)}**"

        await self.view_guilds(ctx, [g for g, c in guilds], f"Command Usage ({commands})", page_length, insert_function=insert_function)

    @baron_view.command(name="unchunked")
    async def baron_view_unchunked(
        self,
        ctx: commands.Context,
        page_length: Optional[int] = 500,
    ):
        """View unchunked servers."""
        guilds = [g for g in self.bot.guilds if not g.chunked]
        if not guilds:
            return await ctx.send(f"There are no unchunked servers.")

        def insert_function(guild: discord.Guild):
            members = len(guild.members)
            percent = members/guild.member_count
            return f"Members Cached: **{humanize_number(members)} ({round(percent, 2)})%**"

        await self.view_guilds(ctx, guilds, "Unchunked Servers", page_length, insert_function=insert_function)

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
    async def baron_leave_botfarms(self, ctx: commands.Context, rate: int = 75):
        """Leave servers with the given bot to member ratio."""
        if rate not in range(1, 100):
            raise commands.BadArgument
        guilds = (await self.get_bot_farms(rate / 100))[0]
        if not guilds[0]:
            await ctx.send(
                f"There are no servers with a bot ratio higher or equal than {rate}%."
            )
            return
        await self.leave_guilds(
            ctx,
            guilds,
            f"I have automatically left this server since it has a high bot to member ratio.",
        )

    @baron_leave.command(name="members")
    async def baron_leave_members(self, ctx: commands.Context, members: int):
        """Leave all servers that have less members than the given number."""
        guilds = [guild for guild in self.bot.guilds if guild.member_count < members]
        if not guilds:
            await ctx.send(f"There are no servers with a member count less than {members}.")
        await self.leave_guilds(
            ctx,
            guilds,
            f"I have automatically left this server since it has less than {members} members.",
        )

    @baron_leave.command(name="blacklisted")
    async def baron_leave_blacklisted(self, ctx: commands.Context):
        """Leave all servers that are blacklisted (in case of downtime)."""
        blacklist = await self.config.blacklist()
        guilds = [g for g in self.bot.guilds if g.id in blacklist]
        if not guilds:
            return await ctx.send(f"I'm not in any blacklisted servers.")
        await self.leave_guilds(ctx, guilds, None, notify_guilds=False)

    @commands.check(comstats_cog)
    @baron_leave.command(name="commands")
    async def baron_leave_commands(self, ctx: commands.Context, commands: int):
        """Leave all servers that have used less commands than the given number."""
        cog = self.bot.get_cog("CommandStats")
        data = await cog.config.guilddata()
        guilds = []

        for guild in self.bot.guilds:
            try:
                guild_data = data[str(guild.id)]
            except KeyError:
                guilds.append(guild)
            else:
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
        )

    @baron.command(name="chunk")
    async def baron_chunk(self, ctx: commands.Context):
        """
        Chunk unchunked servers.

        Credits to KableKompany
        """
        unchunked = [g for g in self.bot.guilds if not g.chunked]
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

    async def leave_guilds(self, ctx: commands.Context, guilds: list, message: str, *, notify_guilds: bool = True):
        data = await self.config.all()
        unwl_guilds = [guild for guild in guilds if guild.id not in data["whitelist"]]
        if not unwl_guilds:
            await ctx.send("There are no servers to leave that aren't whitelisted.")
            return
        name_ids = "\n".join([f"{guild.name} - ({guild.id})" for guild in unwl_guilds][:5])
        guild_preview = name_ids + (
            f"\nand {len(unwl_guilds) - 5} other servers.." if len(unwl_guilds) > 5 else ""
        )

        msg = await ctx.send(
            f"Are you sure you want me to leave the following {len(unwl_guilds)} servers?\n"
            + box(guild_preview, "py")
        )
        start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
        pred = ReactionPredicate.yes_or_no(msg, ctx.author)
        try:
            await self.bot.wait_for("reaction_add", check=pred, timeout=60)
        except asyncio.TimeoutError:
            return await ctx.send("Action cancelled.")

        if pred.result is True:
            async with ctx.typing():
                for guild in unwl_guilds:
                    if notify_guilds:
                        await self.notify_guild(guild, message)
                    await guild.leave()
                await self.baron_log("mass_leave", guilds=unwl_guilds, author=ctx.author)
            await ctx.send(f"Done. I left {len(unwl_guilds)} servers.")
        else:
            await ctx.send("Action cancelled.")

    async def get_bot_farms(self, rate: float):
        bot_farms = []
        ok_guilds = 0
        for guild in self.bot.guilds:
            bots = len([x for x in guild.members if x.bot])
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
        data = await self.config.all()
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
            e.set_author(name=guild.name, icon_url=guild.icon_url)
            await channel.send(embed=e)
        elif log_type == "min_member_leave":
            e = discord.Embed(
                title="Minimum Member Leave",
                description=f"I left {guild.name} since it has less than {data['min_members']} members. ({guild.member_count})",
            )
            e.set_author(name=guild.name, icon_url=guild.icon_url)
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
            e.set_author(name=guild.name, icon_url=guild.icon_url)
            await channel.send(embed=e)
        elif log_type == "bl_leave":
            e = discord.Embed(
                title="Blacklist Leave",
                description=f"I left {guild.name} since it was in the blacklist.",
            )
            e.set_author(name=guild.name, icon_url=guild.icon_url)
            await channel.send(embed=e)

    async def notify_guild(self, guild: discord.Guild, message: str):
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            await guild.system_channel.send(message)
        else:
            for channel in [
                channel for channel in guild.channels if isinstance(channel, discord.TextChannel)
            ]:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send(message)
                    break

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        data = await self.config.all()
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
            ): # adds coverage for the case where bot is already pulling chunk 
            await guild.chunk()
        if data["min_members"] and guild.member_count < data["min_members"]:
            await self.notify_guild(
                guild,
                f"I have automatically left this server since it has less than {data['min_members']} members.",
            )
            await guild.leave()
            await self.baron_log("min_member_leave", guild=guild)
        elif data["bot_ratio"] and (
            len([x for x in guild.members if x.bot]) / guild.member_count
        ) > (data["bot_ratio"] / 100):
            await self.notify_guild(
                guild,
                f"I have automatically left this server since it has a high bot to member ratio.",
            )
            await guild.leave()
            await self.baron_log("botfarm_leave", guild=guild)
