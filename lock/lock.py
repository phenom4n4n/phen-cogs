from typing import Literal, Union, Optional

import discord
from redbot.core import commands, checks
from redbot.core.bot import Red
from redbot.core.config import Config

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class Lock(commands.Cog):
    """
    Lock channels
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=52834582367672349,
            force_registration=True,
        )

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        return

    @checks.bot_has_permissions(manage_channels=True)
    @checks.admin_or_permissions(manage_channels=True)
    @commands.group(invoke_without_command=True)
    async def lock(self, ctx, *, channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None, role: Optional[discord.Role] = None):
        """Lock a channel. Provide a role if you would like to unlock it for that role."""
        if not channel:
            channel = ctx.channel
        if not role:
            role = ctx.guild.default_role
        if isinstance(channel, discord.TextChannel):
            current_perms = channel.overwrites_for(role)
            if current_perms.send_messages == False:
                return await ctx.send(f"{channel.mention} is already locked for `{role}`.")
            current_perms.update(send_messages=False)
            await channel.set_permissions(role, overwrite=current_perms)
            await ctx.tick()
        elif isinstance(channel, discord.VoiceChannel):
            current_perms = channel.overwrites_for(role)
            if current_perms.connect == False:
                return await ctx.send(f"{channel.mention} is already locked for `{role}`.")
            current_perms.update(connect=False)
            await channel.set_permissions(role, overwrite=current_perms)
            await ctx.tick()

    @checks.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_roles=True)
    @lock.command(name="server")
    async def lock_server(self, ctx, *, role: Optional[discord.Role] = None):
        """Lock the server. Provide a role if you would like to lock it for that role."""
        if not role:
            role = ctx.guild.default_role
        if ctx.guild.me.top_role.position <= role.position:
            return await ctx.send("I cannot unlock the server for that role, as I am below it in heirarchy.")
        current_perms = role.permissions 
        if current_perms.send_messages == False:
            return await ctx.send(f"The server is already locked for `{role.name}`.")
        current_perms.update(send_messages=False)
        await role.edit(permissions=current_perms)
        await ctx.tick()

    @checks.bot_has_permissions(manage_channels=True)
    @checks.admin_or_permissions(manage_channels=True)
    @commands.group(invoke_without_command=True)
    async def unlock(self, ctx, *, channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None, role: Optional[discord.Role] = None):
        """Unlock a channel. Provide a role if you would like to unlock it for that role."""
        if not channel:
            channel = ctx.channel
        if not role:
            role = ctx.guild.default_role
        if isinstance(channel, discord.TextChannel):
            current_perms = channel.overwrites_for(role)
            if current_perms.send_messages != False:
                return await ctx.send(f"{channel.mention} is already unlocked for `{role}`.")
            current_perms.update(send_messages=None)
            await channel.set_permissions(role, overwrite=current_perms)
            await ctx.tick()
        elif isinstance(channel, discord.VoiceChannel):
            current_perms = channel.overwrites_for(role)
            if current_perms.connect != False:
                return await ctx.send(f"{channel.mention} is already locked for `{role}`.")
            current_perms.update(connect=False)
            await channel.set_permissions(role, overwrite=current_perms)
            await ctx.tick()

    @checks.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_roles=True)
    @unlock.command(name="server")
    async def unlock_server(self, ctx, *, role: Optional[discord.Role] = None):
        """Unlock the server. Provide a role if you would like to unlock it for that role."""
        if not role:
            role = ctx.guild.default_role
        if ctx.guild.me.top_role.position <= role.position:
            return await ctx.send("I cannot unlock the server for that role, as I am below it in heirarchy.")
        current_perms = role.permissions 
        if current_perms.send_messages == True:
            return await ctx.send(f"The server is already unlocked for `{role.name}`.")
        current_perms.update(send_messages=True)
        await role.edit(permissions=current_perms)
        await ctx.tick()
