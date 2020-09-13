from typing import Literal, Union, Optional
import discord

from redbot.core import commands, checks
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import humanize_list, inline

from .converters import channel_toggle

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
        return

    @checks.bot_has_permissions(manage_channels=True)
    @checks.admin_or_permissions(manage_channels=True)
    @commands.group(invoke_without_command=True)
    async def lock(
        self,
        ctx: commands.Context,
        channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None,
        roles: commands.Greedy[discord.Role] = None,
    ):
        """Lock a channel. Provide a role if you would like to unlock it for that role."""
        if not channel:
            channel = ctx.channel
        if not roles:
            roles = [ctx.guild.default_role]
        succeeded = []
        cancelled = []
        failed = []

        if isinstance(channel, discord.TextChannel):
            for role in roles:
                current_perms = channel.overwrites_for(role)
                my_perms = channel.overwrites_for(ctx.me)
                if my_perms.send_messages != True:
                    my_perms.update(send_messages=True)
                    await channel.set_permissions(ctx.me, overwrite=my_perms)
                if current_perms.send_messages == False:
                    cancelled.append(inline(role.name))
                else:
                    current_perms.update(send_messages=False)
                    try:
                        await channel.set_permissions(role, overwrite=current_perms)
                        succeeded.append(inline(role.name))
                    except:
                        failed.append(inline(role.name))
        elif isinstance(channel, discord.VoiceChannel):
            for role in roles:
                current_perms = channel.overwrites_for(role)
                if current_perms.connect == False:
                    cancelled.append(inline(role.name))
                else:
                    current_perms.update(connect=False)
                    try:
                        await channel.set_permissions(role, overwrite=current_perms)
                        succeeded.append(inline(role.name))
                    except:
                        failed.append(inline(role.name))

        if cancelled:
            await ctx.send(f"{channel.mention} was already locked for {humanize_list(cancelled)}.")
        if succeeded:
            await ctx.send(f"{channel.mention} has been locked for {humanize_list(succeeded)}.")
        if failed:
            await ctx.send(f"I failed to lock {channel.mention} for {humanize_list(failed)}")

    @checks.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_roles=True)
    @lock.command(name="server")
    async def lock_server(self, ctx, roles: commands.Greedy[discord.Role] = None):
        """Lock the server. Provide a role if you would like to lock it for that role."""
        if not roles:
            roles = [ctx.guild.default_role]
        succeeded = []
        cancelled = []
        failed = []

        for role in roles:
            current_perms = role.permissions
            if ctx.guild.me.top_role.position <= role.position:
                failed.append(inline(role.name))
            elif current_perms.send_messages == False:
                cancelled.append(inline(role.name))
            else:
                current_perms.update(send_messages=False)
                try:
                    await role.edit(permissions=current_perms)
                    succeeded.append(inline(role.name))
                except:
                    failed.append(inline(role.name))

        if cancelled:
            await ctx.send(f"The server was already locked for {humanize_list(cancelled)}.")
        if succeeded:
            await ctx.send(f"The server has locked for {humanize_list(succeeded)}.")
        if failed:
            await ctx.send(
                f"I failed to lock the server for {humanize_list(failed)}, probably because I was lower than the roles in heirarchy."
            )

    @checks.bot_has_permissions(manage_channels=True)
    @checks.admin_or_permissions(manage_channels=True)
    @commands.group(invoke_without_command=True)
    async def unlock(
        self,
        ctx,
        channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None,
        state: Optional[channel_toggle] = None,
        roles: commands.Greedy[discord.Role] = None,
    ):
        """Unlock a channel. Provide a role if you would like to unlock it for that role.

        If you would like to override-unlock for a roles, you can do so by pass `true` as the state argument."""
        if not channel:
            channel = ctx.channel
        if not roles:
            roles = [ctx.guild.default_role]
        succeeded = []
        cancelled = []
        failed = []

        if isinstance(channel, discord.TextChannel):
            for role in roles:
                current_perms = channel.overwrites_for(role)
                if current_perms.send_messages != False and current_perms.send_messages == state:
                    cancelled.append(inline(role.name))
                else:
                    current_perms.update(send_messages=state)
                    try:
                        await channel.set_permissions(role, overwrite=current_perms)
                        succeeded.append(inline(role.name))
                    except:
                        failed.append(inline(role.name))
        elif isinstance(channel, discord.VoiceChannel):
            for role in roles:
                current_perms = channel.overwrites_for(role)
                if current_perms.connect != False and current_perms.connect != state:
                    cancelled.append(inline(role.name))
                else:
                    current_perms.update(connect=state)
                    try:
                        await channel.set_permissions(role, overwrite=current_perms)
                        succeeded.append(inline(role.name))
                    except:
                        failed.append(inline(role.name))

        if cancelled:
            await ctx.send(
                f"{channel.mention} was already unlocked for {humanize_list(cancelled)} with state `{'true' if state else 'default'}`."
            )
        if succeeded:
            await ctx.send(
                f"{channel.mention} has unlocked for {humanize_list(succeeded)} with state `{'true' if state else 'default'}`."
            )
        if failed:
            await ctx.send(f"I failed to unlock {channel.mention} for {humanize_list(failed)}")

    @checks.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_roles=True)
    @unlock.command(name="server")
    async def unlock_server(self, ctx, roles: commands.Greedy[discord.Role] = None):
        """Unlock the server. Provide a role if you would like to unlock it for that role."""
        if not roles:
            roles = [ctx.guild.default_role]
        succeeded = []
        cancelled = []
        failed = []

        for role in roles:
            current_perms = role.permissions
            if ctx.guild.me.top_role.position <= role.position:
                failed.append(inline(role.name))
            elif current_perms.send_messages == True:
                cancelled.append(inline(role.name))
            else:
                current_perms.update(send_messages=True)
                try:
                    await role.edit(permissions=current_perms)
                    succeeded.append(inline(role.name))
                except:
                    failed.append(inline(role.name))

        if cancelled:
            await ctx.send(f"The server was already unlocked for {humanize_list(cancelled)}.")
        if succeeded:
            await ctx.send(f"The server has unlocked for {humanize_list(succeeded)}.")
        if failed:
            await ctx.send(
                f"I failed to unlock the server for {humanize_list(failed)}, probably because I was lower than the roles in heirarchy."
            )
