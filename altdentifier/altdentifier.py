import discord
import aiohttp
import asyncio
import typing

from redbot.core import commands, checks, Config
from redbot.core.utils.chat_formatting import box, humanize_list


class AltDentifier(commands.Cog):
    """
    Check new users with AltDentifier API
    """

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.config = Config.get_conf(
            self,
            identifier=60124753086205362,
            force_registration=True,
        )
        default_guild = {
            "channel": None,
            "actions": {"0": None, "1": None, "2": None, "3": None},
            "whitelist": [],
        }

        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(self, **kwargs):
        return

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    @checks.mod_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.command()
    async def altcheck(self, ctx, *, member: discord.Member = None):
        """Check a user on AltDentifier."""

        if not member:
            member = ctx.author
        if member.bot:
            return await ctx.send("Bots can't really be alts you know..")
        trust = await self.alt_request(member)
        e = await self.gen_alt_embed(trust, member)
        await ctx.send(embed=e)

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group()
    async def altset(self, ctx):
        """AltDentifier Settings"""

        if not ctx.subcommand_passed:
            data = await self.config.guild(ctx.guild).all()
            description = []

            if data["channel"]:
                channel = f"<#{data['channel']}>"
            else:
                channel = "None"

            description.append(f"AltDentifier Check Channel: {channel}")
            description = "\n".join(description)
            actionsDict = data["actions"]
            actions = []
            for key, value in actionsDict.items():
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

        This also works as a toggle, so if no channel is provided, it will disable reminders for this server."""

        if not channel:
            await self.config.guild(ctx.guild).channel.clear()
            await ctx.send("Disabled AltDentifier join checks in this server.")
        else:
            if not (
                channel.permissions_for(ctx.me).send_messages
                and channel.permissions_for(ctx.me).send_messages
            ):
                await ctx.send("I do not have permission to talk/send embeds in that channel.")
        await ctx.tick()

    @altset.command()
    async def action(self, ctx, level: int, action: typing.Union[discord.Role, str] = None):
        """Specify what actions to take when a member joins and has a certain Trust Level.

        Leave this empty to remove actions for the Level.
        The available actions are:
        `kick`
        `ban`
        `role` (don't say 'role' for this, pass an actual role."""
        if not level in range(4):
            return await ctx.send(
                "This is not a valid Trust Level. The valid Levels are: 0, 1, 2, and 3."
            )
        if not action:
            await self.clear_action(ctx.guild, level)
            return await ctx.send(f"Removed actions for Trust Level {level}.")
        if isinstance(action, discord.Role):
            if action.position >= ctx.author.top_role.position:
                await ctx.send(
                    f"That role is higher than you in heirarchy, so you can't set it to be the role for this action."
                )
                return
            elif action.position >= ctx.me.top_role.position:
                await ctx.send(
                    f"That role is higher than me in heirarchy, so I can't give it to members for this action."
                )
                return
            async with self.config.guild(ctx.guild).actions() as a:
                a[level] = action.id
        elif isinstance(action, str) and action.lower() not in ["kick", "ban"]:
            return await ctx.send(
                "This is not a valid action. The valid actions are kick and ban. For roles, supply a role."
            )
        else:
            async with self.config.guild(ctx.guild).actions() as a:
                a[level] = action.lower()
        await ctx.tick()

    @altset.command(aliases=["wl"])
    async def whitelist(self, ctx, user_id: int):
        """Whitelist a user from AltDentifier actions."""
        async with self.config.guild(ctx.guild).whitelist() as w:
            w.append(user_id)
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
        await ctx.tick()

    async def alt_request(self, member: discord.Member):
        async with self.session.get(
            f"https://altdentifier.com/api/v2/user/{member.id}/trustfactor"
        ) as response:
            response = await response.json()
        return response["trustfactor"], response["formatted_trustfactor"]

    async def pick_color(self, trustfactor: int):
        if trustfactor == 0:
            color = discord.Color.dark_red()
        elif trustfactor == 1:
            color = discord.Color.red()
        elif trustfactor == 2:
            color = discord.Color.green()
        elif trustfactor == 3:
            color = discord.Color.dark_green()
        return color

    async def gen_alt_embed(
        self, trust: tuple, member: discord.Member, *, actions: typing.Optional[str] = None
    ):
        color = await self.pick_color(trust[0])
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

    async def take_action(self, member: discord.Member, trust: int, actions: dict):
        action = actions[str(trust)]
        reason = f"AltDentifier action taken for Trust Level {trust}"
        if action == "ban":
            try:
                await member.ban(reason=reason)
                return f"Banned for being Trust Level {trust}."
            except discord.errors.Forbidden:
                await self.clear_action(member.guild, trust)
        elif action == "kick":
            try:
                await member.kick(reason=reason)
                return f"Kicked for being Trust Level {trust}."
            except discord.errors.Forbidden:
                await self.clear_action(member.guild, trust)
        elif action:
            role = member.guild.get_role(action)
            if role:
                try:
                    await member.add_roles(role, reason=reason)
                    return f"{role.mention} given for being Trust Level {trust}."
                except discord.errors.Forbidden:
                    await self.clear_action(member.guild, trust)
            else:
                await self.clear_action(member.guild, trust)
        else:
            return None

    async def clear_action(self, guild: discord.Guild, action: int):
        async with self.config.guild(guild).actions() as a:
            a[str(action)] = None

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return
        data = await self.config.guild(member.guild).all()
        if not data["channel"]:
            return
        channel = member.guild.get_channel(data["channel"])
        if not channel:
            await self.config.guild(member.guild).channel.clear()
            return
        trust = await self.alt_request(member)
        if member.id in data["whitelist"]:
            action = "This user was whitelisted so no actions were taken."
        else:
            action = await self.take_action(member, trust[0], data["actions"])
        e = await self.gen_alt_embed(trust, member, actions=action)
        try:
            await channel.send(embed=e)
        except discord.errors.Forbidden:
            await self.config.guild(member.guild).channel.clear()
