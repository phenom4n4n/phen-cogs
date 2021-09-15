import asyncio
import logging
import re
from datetime import timedelta

import discord
from redbot.core import Config, commands, modlog
from redbot.core.utils.chat_formatting import humanize_number
from redbot.core.utils.predicates import MessagePredicate

log = logging.getLogger("red.phenom4n4n.antihonde")


class AntiHonde(commands.Cog):
    __version__ = "1.0.1"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=268562382173765643)
        self.config.register_guild(enabled=False, banned=[])
        self.config.register_global(banned=[])
        self.h0nde_re = re.compile(r"h[0o]nd[ea]", flags=re.I)
        self.enabled = set()

    async def initialize(self):
        for guild_id, guild_data in (await self.config.all_guilds()).items():
            if guild_data["enabled"]:
                self.enabled.add(guild_id)

    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def antihonde(self, ctx: commands.Context, true_or_false: bool = None):
        """
        Toggles automatically banning H0nde when they join the server.
        """
        target_state = (
            true_or_false
            if true_or_false is not None
            else not await self.config.guild(ctx.guild).enabled()
        )
        if target_state:
            now = "now"
            self.enabled.add(ctx.guild.id)
        else:
            now = "no longer"
            try:
                self.enabled.remove(ctx.guild.id)
            except KeyError:
                pass
        await ctx.send(f"I will {now} automatically ban H0nde when they join this server.")
        await self.config.guild(ctx.guild).enabled.set(target_state)

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 60 * 60, commands.BucketType.guild)
    @commands.admin_or_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def purgehonde(self, ctx: commands.Context):
        """
        Ban all "H0nde" alt accounts in this server.
        """
        guild: discord.Guild = ctx.author.guild
        if not guild.chunked:
            await guild.chunk()
        me = guild.me
        hondes = []
        for member in guild.members:
            if not self.is_honde(member):
                continue
            if me.top_role <= member.top_role:
                continue
            hondes.append(member)
        if not hondes:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("There's no H0ndes below me in heirarchy to ban.")

        number = f"**{humanize_number(len(hondes))}**"
        if not ctx.assume_yes:
            await ctx.send(f"Would you like to ban {number} H0ndes?")
            pred = MessagePredicate.yes_or_no(ctx)
            try:
                await self.bot.wait_for("message", check=pred, timeout=60)
            except asyncio.TimeoutError:
                await ctx.send("Timed out, not banning H0ndes.")
                ctx.command.reset_cooldown(ctx)
                return
            if not pred.result:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("Alright, not banning H0ndes.")
        banned = 0
        for honde in hondes:
            await self.ban_honde(honde)
            banned += 1
        await ctx.send(f"Banned {banned} H0nde accounts.")

    def is_honde(self, member: discord.Member) -> bool:
        two_weeks = timedelta(weeks=2)
        if (discord.utils.utcnow() - member.created_at) > two_weeks:
            return False
        return bool(self.h0nde_re.search(member.name))

    async def ban_honde(self, member: discord.Member):
        guild: discord.Guild = member.guild
        async with self.config.banned() as banned:
            banned.append(member.id)
        async with self.config.guild(guild).banned() as guild_banned:
            guild_banned.append(member.id)
        try:
            await member.ban(reason="User Scraper H0nde")
        except discord.NotFound:
            pass
        await modlog.create_case(
            self.bot,
            guild,
            discord.utils.utcnow(),
            "ban",
            member,
            guild.me,
            "User Scraper H0nde",
            until=None,
            channel=None,
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild: discord.Guild = member.guild
        if guild.id not in self.enabled:
            return
        if not self.is_honde(member):
            return
        me = guild.me
        if not me.guild_permissions.ban_members:
            return
        if me.top_role <= member.top_role:
            return
        await self.ban_honde(member)
