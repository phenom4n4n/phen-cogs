import asyncio
from typing import Literal

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import box, humanize_list, pagify
from redbot.core.utils.menus import (DEFAULT_CONTROLS, close_menu, menu,
                                     start_adding_reactions)
from redbot.core.utils.predicates import ReactionPredicate

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


def comstats_cog(ctx: commands.Context):
    return ctx.bot.get_cog("CommandStats") is not None


class Baron(commands.Cog):
    """
    Tools for managing guild joins and leaves.
    """

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
    @commands.group()
    async def baron(self, ctx: commands.Context):
        """Baron's watchtower."""
        if not ctx.subcommand_passed:
            data = await self.config.all()
            description = (
                f"Server Limit: {data['limit'] if data['limit'] else 'Disabled'}\n"
                f"Minimum Members: {data['min_members'] if data['min_members'] else 'Disabled'}\n"
                f"Bot Farm: {data['bot_ratio'] if data['bot_ratio'] else 'Disabled'}\n"
                f"Log Channel: <#{data['log_channel']}>"
            )
            e = discord.Embed(
                color=await ctx.embed_color(),
                title="Baron Settings",
                description=description,
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
    async def minmembers(self, ctx: commands.Context, limit: int = 0):
        """Set the minimum number of members a server should have for the bot to stay in it.

        Pass 0 to disable."""
        await self.config.min_members.set(limit)
        await ctx.send(
            f"The minimum member limit has been set to {limit}."
            if limit
            else "The minimum member limit has been disabled."
        )

    @baron.command()
    async def botratio(self, ctx: commands.Context, ratio: int = 0):
        """Set the bot ratio for servers for the bot to leave.

        Pass 0 to disable."""
        if ratio not in range(0, 100):
            raise commands.BadArgument
        await self.config.bot_ratio.set(ratio)
        await ctx.send(
            f"The bot ratio has been set to {ratio}."
            if ratio
            else "The bot ratio has been removed."
        )

    @baron.command()
    async def botfarms(self, ctx: commands.Context, rate: int = 75, page_limit: int = 500):
        """View servers that have a bot to member ratio with the given rate."""
        if rate not in range(1, 100):
            raise commands.BadArgument
        if page_limit > 2000 or page_limit <= 0:
            raise commands.BadArgument
        rate = rate / 100
        msg = ""
        data = await self.config.all()

        bot_farms = await self.get_bot_farms(rate)
        for guild in bot_farms[0]:
            bots = len([x for x in guild.members if x.bot])
            percent = bots / len(guild.members)
            percent = bots / len(guild.members)
            msg += f"{guild.name} - ({guild.id})\n"
            msg += f"Bots: **{percent * 100}%**\n"
            msg += f"Members: **{len(guild.members)}**\n"
            if guild.id in data["whitelist"]:
                msg += f"[Whitelisted](https://www.youtube.com/watch?v=oHg5SJYRHA0)\n"
            msg += "\n"
        if msg:
            color = discord.Color.red()
        else:
            msg = f"There are no servers with a bot ratio higher or equal than {rate * 100}%."
            color = discord.Color.green()
        if len(msg) > page_limit:
            embeds = []
            pages = list([page for page in pagify(msg, ["\n\n"], page_length=page_limit)])
            for index, page in enumerate(pages, 1):
                e = discord.Embed(
                    color=color,
                    title="Bot Farms Check",
                    description=page,
                )
                e.set_footer(text=f"OK guilds: {bot_farms[1]} | {index}/{len(pages)}")
                embeds.append(e)
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e = discord.Embed(
                color=color,
                title="Bot Farms Check",
                description=msg,
            )
            e.set_footer(text=f"OK guilds: {bot_farms[1]}")
            emoji = self.bot.get_emoji(736038541364297738) or "🚫"
            await menu(ctx, [e], {emoji: close_menu})

    @baron.command()
    async def members(
        self, ctx: commands.Context, members: int, less_than: bool = True, page_limit: int = 500
    ):
        """View servers that have a member count less than the specified number.

        Pass False at the end if you would like to view servers that are greater than the specified number."""
        if less_than:
            guilds = [guild for guild in self.bot.guilds if len(guild.members) < members]
        else:
            guilds = [guild for guild in self.bot.guilds if len(guild.members) > members]
        data = await self.config.all()
        msg = ""

        for guild in guilds:
            bots = len([x for x in guild.members if x.bot])
            percent = bots / len(guild.members)
            percent = bots / len(guild.members)
            msg += f"{guild.name} - ({guild.id})\n"
            msg += f"Bots: **{percent * 100}%**\n"
            msg += f"Members: **{len(guild.members)}**\n"
            if guild.id in data["whitelist"]:
                msg += f"[Whitelisted](https://www.youtube.com/watch?v=oHg5SJYRHA0)\n"
            msg += "\n"
        if msg:
            color = discord.Color.red()
        else:
            msg = (
                f"There are no servers with a member count {'less' if less_than else 'greater'} than "
                f"{members}."
            )
            color = discord.Color.green()
        if len(msg) > page_limit:
            embeds = []
            pages = list([page for page in pagify(msg, ["\n\n"], page_length=page_limit)])
            for index, page in enumerate(pages, 1):
                e = discord.Embed(
                    color=color,
                    title="Server Members Check",
                    description=page,
                )
                e.set_footer(text=f"{index}/{len(pages)}")
                embeds.append(e)
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e = discord.Embed(
                color=color,
                title="Server Members Check",
                description=msg,
            )
            emoji = self.bot.get_emoji(736038541364297738) or "🚫"
            await menu(ctx, [e], {emoji: close_menu})

    @commands.check(comstats_cog)
    @baron.command(name="commands")
    async def view_commands(
        self,
        ctx: commands.Context,
        commands: int,
        highest_first: bool = False,
        page_limit: int = 500,
    ):
        """View servers that have command usage less than the specified number.

        Pass True at the end if you would like to view servers in order of most commands used."""
        cog = self.bot.get_cog("CommandStats")
        data = await cog.config.guilddata()
        guilds = []

        for guild in self.bot.guilds:
            try:
                guild_data = data[str(guild.id)]
            except KeyError:
                guilds.append((guild, 0))
            else:
                total_commands = 0
                for value in guild_data.values():
                    total_commands += value
                if total_commands < commands:
                    guilds.append((guild, total_commands))
        guilds.sort(key=lambda x: x[1], reverse=highest_first)

        data = await self.config.all()
        msg = ""

        for guild, usage in guilds:
            bots = len([x for x in guild.members if x.bot])
            percent = bots / len(guild.members)
            percent = bots / len(guild.members)
            msg += f"{guild.name} - ({guild.id})\n"
            msg += f"Commands Used: **{usage}**\n"
            msg += f"Bots: **{percent * 100}%**\n"
            msg += f"Members: **{len(guild.members)}**\n"
            if guild.id in data["whitelist"]:
                msg += f"[Whitelisted](https://www.youtube.com/watch?v=oHg5SJYRHA0)\n"
            msg += "\n"
        if msg:
            color = discord.Color.red()
        else:
            msg = f"There are no servers with command usage less than {commands}."
            color = discord.Color.green()

        if len(msg) > page_limit:
            embeds = []
            pages = list([page for page in pagify(msg, ["\n\n"], page_length=page_limit)])
            for index, page in enumerate(pages, 1):
                e = discord.Embed(
                    color=color,
                    title="Command Usage Check",
                    description=page,
                )
                e.set_footer(text=f"{index}/{len(pages)}")
                embeds.append(e)
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e = discord.Embed(
                color=color,
                title="Command Usage Check",
                description=msg,
            )
            emoji = self.bot.get_emoji(736038541364297738) or "🚫"
            await menu(ctx, [e], {emoji: close_menu})

    @baron.group()
    async def leave(self, ctx: commands.Context):
        """Manage leaving servers."""
        pass

    @leave.command()
    async def mass(self, ctx: commands.Context, guilds: commands.Greedy[commands.GuildConverter]):
        """Leave servers from a list of IDs."""
        if not guilds:
            raise commands.BadArgument
        await self.leave_guilds(ctx, guilds, "I have left this server at the request of my owner.")

    @leave.command(name="botfarms")
    async def leave_botfarms(self, ctx: commands.Context, rate: int = 75):
        """Leave servers with the given bot to member ratio."""
        if rate not in range(1, 100):
            raise commands.BadArgument
        rate = rate / 100
        guilds = (await self.get_bot_farms(rate))[0]
        if not guilds[0]:
            await ctx.send(
                f"There are no servers with a bot ratio higher or equal than {rate * 100}%."
            )
            return
        await self.leave_guilds(
            ctx,
            guilds,
            f"I have automatically left this server since it has a high bot to member ratio.",
        )

    @leave.command(name="members")
    async def leave_members(self, ctx: commands.Context, members: int):
        """Leave all servers that have less members than the given number."""
        guilds = [guild for guild in self.bot.guilds if len(guild.members) < members]
        if not guilds:
            await ctx.send(f"There are no servers with a member count less than {members}.")
        await self.leave_guilds(
            ctx,
            guilds,
            f"I have automatically left this server since it has less than {members} members.",
        )

    async def leave_guilds(self, ctx: commands.Context, guilds: list, message: str):
        data = await self.config.all()
        unwl_guilds = [guild for guild in guilds if guild.id not in data["whitelist"]]
        if not unwl_guilds:
            await ctx.send("There are no servers to leave that aren't whitelisted.")
            return
        name_ids = "\n".join([f"{guild.name} - ({guild.id})" for guild in unwl_guilds][:5])
        guild_preview = name_ids + (
            f"\nand {len(unwl_guilds) - 5} other guilds.." if len(unwl_guilds) > 5 else ""
        )

        msg = await ctx.send(
            f"Are you sure you want me to leave the following {len(unwl_guilds)} guilds?\n"
            + box(guild_preview, "py")
        )
        start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
        pred = ReactionPredicate.yes_or_no(msg, ctx.author)
        try:
            await self.bot.wait_for("reaction_add", check=pred, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send("Action cancelled.")

        if pred.result is True:
            async with ctx.typing():
                for guild in unwl_guilds:
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
            percent = bots / len(guild.members)
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
                description=f"I left {guild.name} since it has less than {data['min_members']} members. ({len(guild.members)})",
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
        elif data["min_members"] and len(guild.members) < data["min_members"]:
            await self.notify_guild(
                guild,
                f"I have automatically left this server since it has less than {data['min_members']} members.",
            )
            await guild.leave()
            await self.baron_log("min_member_leave", guild=guild)
        elif data["bot_ratio"] and (
            len([x for x in guild.members if x.bot]) / len(guild.members)
        ) > (data["bot_ratio"] / 100):
            await self.notify_guild(
                guild,
                f"I have automatically left this server since it has a high bot to member ratio.",
            )
            await guild.leave()
            await self.baron_log("botfarm_leave", guild=guild)
