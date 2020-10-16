from typing import Literal, Optional, Union
from copy import copy
import discord
from redbot.core import checks, commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import humanize_list, inline, box

from .converters import FuzzyRole, channel_toggle

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class Lock(commands.Cog):
    """
    Advanced channel and server locking.
    """
    __version__ = "1.1.0"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=52834582367672349,
            force_registration=True,
        )

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        return

    @checks.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_roles=True)
    @commands.group(invoke_without_command=True)
    async def lock(
        self,
        ctx: commands.Context,
        channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None,
        roles_or_members: commands.Greedy[Union[FuzzyRole, discord.Member]] = None,
    ):
        """Lock a channel. Provide a role or member if you would like to lock it for them.

        You can only lock a maximum of 10 things at once."""
        await ctx.trigger_typing()
        if not channel:
            channel = ctx.channel
        if not roles_or_members:
            roles_or_members = [ctx.guild.default_role]
        else:
            roles_or_members = roles_or_members[:10]
        succeeded = []
        cancelled = []
        failed = []

        if isinstance(channel, discord.TextChannel):
            for role in roles_or_members:
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
            for role in roles_or_members:
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

        msg = ""
        if succeeded:
            msg += f"{channel.mention} has been locked for {humanize_list(succeeded)}.\n"
        if cancelled:
            msg += f"{channel.mention} was already locked for {humanize_list(cancelled)}.\n"
        if failed:
            msg += f"I failed to lock {channel.mention} for {humanize_list(failed)}.\n"
        if msg:
            await ctx.send(msg)

    @checks.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_roles=True)
    @commands.command()
    async def viewlock(
        self,
        ctx: commands.Context,
        channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None,
        roles_or_members: commands.Greedy[Union[FuzzyRole, discord.Member]] = None,
    ):
        """Prevent users from viewing a channel. Provide a role or member if you would like to lock it for them.

        You can only lock a maximum of 10 things at once."""
        await ctx.trigger_typing()
        if not channel:
            channel = ctx.channel
        if not roles_or_members:
            roles_or_members = [ctx.guild.default_role]
        else:
            roles_or_members = roles_or_members[:10]
        succeeded = []
        cancelled = []
        failed = []

        for role in roles_or_members:
            current_perms = channel.overwrites_for(role)
            if current_perms.read_messages == False:
                cancelled.append(inline(role.name))
            else:
                current_perms.update(read_messages=False)
                try:
                    await channel.set_permissions(role, overwrite=current_perms)
                    succeeded.append(inline(role.name))
                except:
                    failed.append(inline(role.name))

        msg = ""
        if succeeded:
            msg += f"{channel.mention} has been viewlocked for {humanize_list(succeeded)}.\n"
        if cancelled:
            msg += f"{channel.mention} was already viewlocked for {humanize_list(cancelled)}.\n"
        if failed:
            msg += f"I failed to viewlock {channel.mention} for {humanize_list(failed)}.\n"
        if msg:
            await ctx.send(msg)

    @lock.command(name="server")
    async def lock_server(self, ctx, roles: commands.Greedy[FuzzyRole] = None):
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
        msg = ""
        if succeeded:
            await ctx.send(f"The server has locked for {humanize_list(succeeded)}.")
        if cancelled:
            await ctx.send(f"The server was already locked for {humanize_list(cancelled)}.")
        if failed:
            await ctx.send(
                f"I failed to lock the server for {humanize_list(failed)}, probably because I was lower than the roles in heirarchy."
            )

    @commands.is_owner() # unstable, incomplete
    @lock.command(name="perms")
    async def lock_perms(
        self,
        ctx: commands.Context,
        channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None,
        roles_or_members: commands.Greedy[Union[FuzzyRole, discord.Member]] = None,
        *permissions: str,
    ):
        """Set the given permissions for a role or member to True."""
        if not permissions:
            raise commands.BadArgument

        await ctx.trigger_typing()
        channel = channel or ctx.channel
        roles_or_members = roles_or_members or [ctx.guild.default_role]

        perms = {}
        for perm in permissions:
            perms.update({perm: False})
        for role in roles_or_members:
            overwrite = self.update_overwrite(ctx, channel.overwrites_for(role), perms)
            await channel.set_permissions(role, overwrite=overwrite[0])
        msg = ""
        if overwrite[1]:
            msg += (
                f"The following permissions have been denied for "
                f"{humanize_list([f'`{obj}`' for obj in roles_or_members])} in {channel.mention}:\n"
                f"{humanize_list([f'`{perm}`' for perm in overwrite[1]])}\n"
            )
        if overwrite[2]:
            msg += overwrite[2]
        if overwrite[3]:
            msg += overwrite[3]
        if msg:
            await ctx.send(msg)

    @checks.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_roles=True)
    @commands.group(invoke_without_command=True)
    async def unlock(
        self,
        ctx,
        channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None,
        state: Optional[channel_toggle] = None,
        roles_or_members: commands.Greedy[Union[FuzzyRole, discord.Member]] = None,
    ):
        """Unlock a channel. Provide a role or member if you would like to unlock it for them.

        If you would like to override-unlock for something, you can do so by pass `true` as the state argument.
        You can only unlock a maximum of 10 things at once."""
        await ctx.trigger_typing()
        if not channel:
            channel = ctx.channel
        if not roles_or_members:
            roles_or_members = [ctx.guild.default_role]
        else:
            roles_or_members = roles_or_members[:10]
        succeeded = []
        cancelled = []
        failed = []

        if isinstance(channel, discord.TextChannel):
            for role in roles_or_members:
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
            for role in roles_or_members:
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

        msg = ""
        if succeeded:
            msg += f"{channel.mention} has unlocked for {humanize_list(succeeded)} with state `{'true' if state else 'default'}`.\n"
        if cancelled:
            msg += f"{channel.mention} was already unlocked for {humanize_list(cancelled)} with state `{'true' if state else 'default'}`.\n"
        if failed:
            msg += f"I failed to unlock {channel.mention} for {humanize_list(failed)}.\n"
        if msg:
            await ctx.send(msg)

    @checks.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_roles=True)
    @commands.group(invoke_without_command=True)
    async def unviewlock(
        self,
        ctx,
        channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None,
        state: Optional[channel_toggle] = None,
        roles_or_members: commands.Greedy[Union[FuzzyRole, discord.Member]] = None,
    ):
        """Allow users to view a channel. Provide a role or member if you would like to unlock it for them.

        If you would like to override-unlock for something, you can do so by pass `true` as the state argument.
        You can only unlock a maximum of 10 things at once."""
        await ctx.trigger_typing()
        if not channel:
            channel = ctx.channel
        if not roles_or_members:
            roles_or_members = [ctx.guild.default_role]
        else:
            roles_or_members = roles_or_members[:10]
        succeeded = []
        cancelled = []
        failed = []

        for role in roles_or_members:
            current_perms = channel.overwrites_for(role)
            if current_perms.read_messages != False and current_perms.read_messages == state:
                cancelled.append(inline(role.name))
            else:
                current_perms.update(read_messages=state)
                try:
                    await channel.set_permissions(role, overwrite=current_perms)
                    succeeded.append(inline(role.name))
                except:
                    failed.append(inline(role.name))

        msg = ""
        if succeeded:
            msg += f"{channel.mention} has unlocked viewing for {humanize_list(succeeded)} with state `{'true' if state else 'default'}`.\n"
        if cancelled:
            msg += f"{channel.mention} was already unviewlocked for {humanize_list(cancelled)} with state `{'true' if state else 'default'}`.\n"
        if failed:
            msg += f"I failed to unlock {channel.mention} for {humanize_list(failed)}.\n"
        if msg:
            await ctx.send(msg)

    @unlock.command(name="server")
    async def unlock_server(self, ctx, roles: commands.Greedy[FuzzyRole] = None):
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

        msg = []
        if succeeded:
            msg.append(f"The server has unlocked for {humanize_list(succeeded)}.")
        if cancelled:
            msg.append(f"The server was already unlocked for {humanize_list(cancelled)}.")
        if failed:
            msg.append(
                f"I failed to unlock the server for {humanize_list(failed)}, probably because I was lower than the roles in heirarchy."
            )
        if msg:
            await ctx.send("\n".join(msg))

    @commands.is_owner() # unstable, incomplete
    @unlock.command(name="perms")
    async def unlock_perms(
        self,
        ctx: commands.Context,
        channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None,
        state: Optional[channel_toggle] = None,
        roles_or_members: commands.Greedy[Union[FuzzyRole, discord.Member]] = None,
        *permissions: str,
    ):
        """Set the given permissions for a role or member to `True` or `None`, depending on the given state"""
        if not permissions:
            raise commands.BadArgument

        await ctx.trigger_typing()
        channel = channel or ctx.channel
        roles_or_members = roles_or_members or [ctx.guild.default_role]

        perms = {}
        for perm in permissions:
            perms.update({perm: state})
        for role in roles_or_members:
            overwrite = self.update_overwrite(ctx, channel.overwrites_for(role), perms)
            await channel.set_permissions(role, overwrite=overwrite[0])
        msg = ""
        if overwrite[1]:
            msg += (
                f"The following permissions have been set to `{state}` for "
                f"{humanize_list([f'`{obj}`' for obj in roles_or_members])} in {channel.mention}:\n"
                f"{humanize_list([f'`{perm}`' for perm in overwrite[1]])}"
            )
        if overwrite[2]:
            msg += overwrite[2]
        if overwrite[3]:
            msg += overwrite[3]
        if msg:
            await ctx.send(msg)

    @staticmethod
    def update_overwrite(ctx: commands.Context, overwrite: discord.PermissionOverwrite, permissions: dict):
        base_perms = dict(iter(discord.PermissionOverwrite()))
        old_perms = copy(permissions)
        user_perms = ctx.channel.permissions_for(ctx.author)
        invalid_perms = []
        valid_perms = []
        not_allowed = []
        for perm in old_perms.keys():
            if perm not in base_perms.keys():
                invalid_perms.append(f"`{perm}`")
                del permissions[perm]
            else:
                valid_perms.append(f"`{perm}`")
        overwrite.update(**permissions)
        if invalid_perms:
            invalid = f"\nThe following permissions were invalid:\n{humanize_list(invalid_perms)}\n"
            possible = humanize_list([f"`{perm}`" for perm in base_perms.keys()])
            invalid += f"Possible permissions are:\n{possible}"
        else:
            invalid = ""
        return overwrite, valid_perms, invalid, not_allowed
