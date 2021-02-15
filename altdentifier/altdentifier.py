import typing
import asyncio

import aiohttp
import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import box, humanize_list

from .converters import ActionConverter, LevelConverter, StrictRole


class APIError(Exception):
    pass


class AltDentifier(commands.Cog):
    """
    Check new users with AltDentifier API
    """

    __version__ = "1.1.0"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\nCog Version: {self.__version__}"

    default_guild = {
        "channel": None,
        "actions": {"0": None, "1": None, "2": None, "3": None},
        "whitelist": [],
    }

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.config = Config.get_conf(
            self,
            identifier=60124753086205362,
            force_registration=True,
        )

        self.config.register_guild(**self.default_guild)
        self.guild_data_cache = {}
        self.task = asyncio.create_task(self.build_cache())

    async def red_delete_data_for_user(self, **kwargs):
        return

    async def build_cache(self):
        self.guild_data_cache = await self.config.all_guilds()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())
        self.task.cancel()

    @checks.mod_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.command()
    async def altcheck(self, ctx, *, member: discord.Member = None):
        """Check a user on AltDentifier."""
        if not member:
            member = ctx.author
        if member.bot:
            return await ctx.send("Bots can't really be alts you know..")
        try:
            trust = await self.alt_request(member)
        except APIError:
            e = self.fail_embed(member)
        else:
            e = self.gen_alt_embed(trust, member)
        await ctx.send(embed=e)

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group()
    async def altset(self, ctx):
        """Manage AltDentifier Settings."""

    @altset.command()
    async def settings(self, ctx: commands.Context):
        """View AltDentifier Settings."""
        data = await self.config.guild(ctx.guild).all()
        description = []

        if data["channel"]:
            channel = f"<#{data['channel']}>"
        else:
            channel = "None"

        description.append(f"AltDentifier Check Channel: {channel}")
        description = "\n".join(description)
        actions = []
        for key, value in data["actions"].items():
            actions.append(f"{key}: {value}")
        actions = box("\n".join(actions))

        color = await self.bot.get_embed_colour(ctx)
        e = discord.Embed(color=color, title=f"AltDentifier Settings", description=description)
        e.add_field(name="Actions", value=actions, inline=False)
        if data["whitelist"]:
            e.add_field(name="Whitelist", value=humanize_list(data["whitelist"]), inline=False)
        e.set_author(name=ctx.guild, icon_url=ctx.guild.icon_url)
        await ctx.send(embed=e)

    @altset.command()
    async def channel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel to send AltDentifier join checks to.

        This also works as a toggle, so if no channel is provided, it will disable join checks for this server."""
        if not channel:
            await self.config.guild(ctx.guild).channel.clear()
            await ctx.send("Disabled AltDentifier join checks in this server.")
        else:
            if not (
                channel.permissions_for(ctx.me).send_messages
                and channel.permissions_for(ctx.me).send_messages
            ):
                await ctx.send("I do not have permission to talk/send embeds in that channel.")
            else:
                await self.config.guild(ctx.guild).channel.set(channel.id)
        await self.build_cache()
        await ctx.tick()

    @altset.command()
    async def action(
        self, ctx, level: LevelConverter, action: typing.Union[discord.Role, str] = None
    ):
        """Specify what actions to take when a member joins and has a certain Trust Level.

        Leave this empty to remove actions for the Level.
        The available actions are:
        `kick`
        `ban`
        `role` (don't say 'role' for this, pass an actual role."""
        if not action:
            await self.clear_action(ctx.guild, level)
            return await ctx.send(f"Removed actions for Trust Level {level}.")
        if isinstance(action, discord.Role):
            try:
                await StrictRole().convert(ctx, str(action.id))
            except commands.BadArgument as e:
                await ctx.send(e)
                return
            async with self.config.guild(ctx.guild).actions() as a:
                a[level] = action.id
        elif isinstance(action, str) and action.lower() not in ["kick", "ban"]:
            try:
                await ActionConverter().convert(ctx, action)
            except commands.BadArgument as e:
                await ctx.send(e)
                return
        else:
            async with self.config.guild(ctx.guild).actions() as a:
                a[level] = action.lower()
        await self.build_cache()
        await ctx.tick()

    @altset.command(aliases=["wl"])
    async def whitelist(self, ctx, user_id: int):
        """Whitelist a user from AltDentifier actions."""
        async with self.config.guild(ctx.guild).whitelist() as w:
            w.append(user_id)
        await self.build_cache()
        await ctx.tick()

    @altset.command(aliases=["unwl"])
    async def unwhitelist(self, ctx, user_id: int):
        """Remove a user from the AltDentifier whitelist."""
        async with self.config.guild(ctx.guild).whitelist() as w:
            try:
                index = w.index(user_id)
            except ValueError:
                return await ctx.send("This user has not been whitelisted.")
            w.pop(index)
        await self.build_cache()
        await ctx.tick()

    async def alt_request(self, member: discord.Member):
        async with self.session.get(
            f"https://altdentifier.com/api/v2/user/{member.id}/trustfactor"
        ) as response:
            if response.status != 200:
                raise APIError
            try:
                response = await response.json()
            except aiohttp.client_exceptions.ContentTypeError:
                raise APIError
        return response["trustfactor"], response["formatted_trustfactor"]

    def pick_color(self, trustfactor: int):
        if trustfactor == 0:
            color = discord.Color.dark_red()
        elif trustfactor == 1:
            color = discord.Color.red()
        elif trustfactor == 2:
            color = discord.Color.green()
        elif trustfactor == 3:
            color = discord.Color.dark_green()
        return color

    def gen_alt_embed(
        self, trust: tuple, member: discord.Member, *, actions: typing.Optional[str] = None
    ):
        color = self.pick_color(trust[0])
        e = discord.Embed(
            color=color,
            title="AltDentifier Check",
            description=f"{member.mention} is {trust[1]}\nTrust Factor: {trust[0]}",
            timestamp=member.created_at,
        )
        if actions:
            e.add_field(name="Actions Taken", value=actions, inline=False)
        e.set_footer(text="Account created at")
        e.set_thumbnail(url=member.avatar_url)
        return e

    def fail_embed(self, member: discord.Member) -> discord.Embed:
        e = discord.Embed(
            color=discord.Color.orange(),
            title="AltDentifier Check Fail",
            description=f"The API encountered an error. Check back later.",
            timestamp=member.created_at,
        )
        e.set_footer(text="Account created at")
        e.set_thumbnail(url=member.avatar_url)
        return e

    async def take_action(
        self, guild: discord.Guild, member: discord.Member, trust: int, actions: dict
    ):
        action = actions[str(trust)]
        reason = f"AltDentifier action taken for Trust Level {trust}"
        result = ""
        try:
            if action == "ban":
                if guild.me.guild_permissions.ban_members:
                    try:
                        await member.ban(reason=reason)
                        result = f"Banned for being Trust Level {trust}."
                    except discord.Forbidden as e:
                        await self.clear_action(guild, trust)
                        result = f"Banning failed.\n{e}"
                else:
                    result = "Banning was skipped due to missing permissions."
            elif action == "kick":
                if guild.me.guild_permissions.kick_members:
                    try:
                        await member.kick(reason=reason)
                        result = f"Kicked for being Trust Level {trust}."
                    except discord.Forbidden as e:
                        await self.clear_action(guild, trust)
                        result = f"Kicking failed.\n{e}"
                else:
                    result = "Kicking was skipped due to missing permissions."
            elif action:
                role = guild.get_role(action)
                if role:
                    if guild.me.guild_permissions.manage_roles:
                        try:
                            await member.add_roles(role, reason=reason)
                            result = f"{role.mention} given for being Trust Level {trust}."
                        except discord.Forbidden as e:
                            await self.clear_action(guild, trust)
                            result = f"Adding role failed.\n{e}"
                else:
                    await self.clear_action(member.guild, trust)
                    result = "Adding the role was skipped due to missing permissions."
        except discord.NotFound as e:
            result = f"The member left before an action could be taken."
        return result

    async def clear_action(self, guild: discord.Guild, action: int):
        async with self.config.guild(guild).actions() as a:
            a[str(action)] = None
        await self.build_cache()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        guild: discord.Guild = member.guild
        if not (data := self.guild_data_cache.get(guild.id)):
            return
        if not (channel_id := data.get("channel")):
            return
        channel = guild.get_channel(channel_id)
        if not channel:
            await self.config.guild(guild).channel.clear()
            return
        try:
            trust = await self.alt_request(member)
        except APIError:
            e = self.fail_embed(member)
            try:
                await channel.send(embed=e)
            except discord.Forbidden:
                await self.config.guild(guild).channel.clear()
        else:
            if member.id in data.get("whitelist", []):
                action = "This user was whitelisted so no actions were taken."
            else:
                action = await self.take_action(
                    guild, member, trust[0], data.get("actions", self.default_guild["actions"])
                )
            e = self.gen_alt_embed(trust, member, actions=action)
            try:
                await channel.send(embed=e)
            except discord.Forbidden:
                await self.config.guild(guild).channel.clear()
