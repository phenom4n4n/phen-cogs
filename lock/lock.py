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

from copy import copy
from typing import List, Literal, Optional, Union

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import humanize_list, inline
from redbot.core.utils.mod import get_audit_reason

from .converters import ChannelToggle, LockableChannel, LockableRole

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class Lock(commands.Cog):
    """
    Advanced channel and server locking.
    """

    __version__ = "1.1.5"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\nCog Version: {self.__version__}"

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=52834582367672349,
            force_registration=True,
        )

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        return

    @commands.bot_has_permissions(manage_roles=True)
    @commands.admin_or_permissions(manage_roles=True)
    @commands.group(invoke_without_command=True)
    async def lock(
        self,
        ctx: commands.Context,
        channel: Optional[Union[LockableChannel, discord.VoiceChannel]] = None,
        roles_or_members: commands.Greedy[Union[LockableRole, discord.Member]] = None,
    ):
        """
        Lock a channel.

        Provide a role or member if you would like to lock it for them.
        You can only lock a maximum of 10 things at once.

        **Examples:**
        `[p]lock #general`
        `[p]lock 737958453905063977 @members`
        """
        try:
            await ctx.typing()
        except discord.Forbidden:
            return

        if not channel:
            channel = ctx.channel
        if not roles_or_members:
            roles_or_members = [ctx.guild.default_role]
        else:
            roles_or_members = roles_or_members[:10]
        succeeded = []
        cancelled = []
        failed = []
        reason = get_audit_reason(ctx.author)

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
                        await channel.set_permissions(role, overwrite=current_perms, reason=reason)
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
                        await channel.set_permissions(role, overwrite=current_perms, reason=reason)
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

    @commands.bot_has_permissions(manage_roles=True)
    @commands.admin_or_permissions(manage_roles=True)
    @commands.command()
    async def viewlock(
        self,
        ctx: commands.Context,
        channel: Optional[Union[LockableChannel, discord.VoiceChannel]] = None,
        roles_or_members: commands.Greedy[Union[LockableRole, discord.Member]] = None,
    ):
        """
        Prevent users from viewing a channel.

        Provide a role or member if you would like to lock it for them.
        You can only lock a maximum of 10 things at once.

        **Example:**
        `[p]viewlock #secret-channel`
        `[p]viewlock 7382395026348520 @nubs`
        """
        try:
            await ctx.typing()
        except discord.Forbidden:
            return

        if not channel:
            channel = ctx.channel
        if not roles_or_members:
            roles_or_members = [ctx.guild.default_role]
        else:
            roles_or_members = roles_or_members[:10]
        succeeded = []
        cancelled = []
        failed = []
        reason = get_audit_reason(ctx.author)

        for role in roles_or_members:
            current_perms = channel.overwrites_for(role)
            if current_perms.read_messages == False:
                cancelled.append(inline(role.name))
            else:
                current_perms.update(read_messages=False)
                try:
                    await channel.set_permissions(role, overwrite=current_perms, reason=reason)
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

    @lock.command("server")
    async def lock_server(self, ctx: commands.Context, *roles: LockableRole):
        """
        Lock the server.

        Provide a role if you would like to lock it for that role.

        **Example:**
        `[p]lock server @members`
        """
        if not roles:
            roles = [ctx.guild.default_role]
        succeeded = []
        cancelled = []
        failed = []

        for role in roles:
            current_perms = role.permissions
            if ctx.guild.me.top_role <= role:
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
        if succeeded:
            await ctx.send(f"The server has locked for {humanize_list(succeeded)}.")
        if cancelled:
            await ctx.send(f"The server was already locked for {humanize_list(cancelled)}.")
        if failed:
            await ctx.send(
                f"I failed to lock the server for {humanize_list(failed)}, probably because I was lower than the roles in heirarchy."
            )

    @commands.is_owner()  # unstable, incomplete
    @lock.command("perms")
    async def lock_perms(
        self,
        ctx: commands.Context,
        channel: Optional[Union[LockableChannel, discord.VoiceChannel]] = None,
        roles_or_members: commands.Greedy[Union[LockableRole, discord.Member]] = None,
        *permissions: str,
    ):
        """Set the given permissions for a role or member to True."""
        if not permissions:
            raise commands.BadArgument

        try:
            await ctx.typing()
        except discord.Forbidden:
            return

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

    @commands.bot_has_permissions(manage_roles=True)
    @commands.admin_or_permissions(manage_roles=True)
    @commands.group(invoke_without_command=True)
    async def unlock(
        self,
        ctx: commands.Context,
        channel: Optional[Union[LockableChannel, discord.VoiceChannel]] = None,
        state: Optional[ChannelToggle] = None,
        roles_or_members: commands.Greedy[Union[LockableRole, discord.Member]] = None,
    ):
        """
        Unlock a channel.

        Provide a role or member if you would like to unlock it for them.
        If you would like to override-unlock for something, you can do so by pass `true` as the state argument.
        You can only unlock a maximum of 10 things at once.

        **Examples:**
        `[p]unlock #general`
        `[p]unlock 739562845027353 true`
        """
        try:
            await ctx.typing()
        except discord.Forbidden:
            return

        if not channel:
            channel = ctx.channel
        if roles_or_members:
            roles_or_members = roles_or_members[:10]
        else:
            roles_or_members = [ctx.guild.default_role]
        succeeded = []
        cancelled = []
        failed = []
        reason = get_audit_reason(ctx.author)

        if isinstance(channel, discord.TextChannel):
            for role in roles_or_members:
                current_perms = channel.overwrites_for(role)
                if current_perms.send_messages != False and current_perms.send_messages == state:
                    cancelled.append(inline(role.name))
                else:
                    current_perms.update(send_messages=state)
                    try:
                        await channel.set_permissions(role, overwrite=current_perms, reason=reason)
                        succeeded.append(inline(role.name))
                    except:
                        failed.append(inline(role.name))
        elif isinstance(channel, discord.VoiceChannel):
            for role in roles_or_members:
                current_perms = channel.overwrites_for(role)
                if current_perms.connect in [False, state]:
                    current_perms.update(connect=state)
                    try:
                        await channel.set_permissions(role, overwrite=current_perms, reason=reason)
                        succeeded.append(inline(role.name))
                    except:
                        failed.append(inline(role.name))
                else:
                    cancelled.append(inline(role.name))

        msg = ""
        if succeeded:
            msg += f"{channel.mention} has unlocked for {humanize_list(succeeded)} with state `{'true' if state else 'default'}`.\n"
        if cancelled:
            msg += f"{channel.mention} was already unlocked for {humanize_list(cancelled)} with state `{'true' if state else 'default'}`.\n"
        if failed:
            msg += f"I failed to unlock {channel.mention} for {humanize_list(failed)}.\n"
        if msg:
            await ctx.send(msg)

    @commands.bot_has_permissions(manage_roles=True)
    @commands.admin_or_permissions(manage_roles=True)
    @commands.group(invoke_without_command=True)
    async def unviewlock(
        self,
        ctx: commands.Context,
        channel: Optional[Union[LockableChannel, discord.VoiceChannel]] = None,
        state: Optional[ChannelToggle] = None,
        roles_or_members: commands.Greedy[Union[LockableRole, discord.Member]] = None,
    ):
        """
        Allow users to view a channel.

        Provide a role or member if you would like to unlock it for them.
        If you would like to override-unlock for something, you can do so by pass `true` as the state argument.
        You can only unlock a maximum of 10 things at once.

        **Example:**
        `[p]unviewlock #hidden-channel true`
        `[p]unviewlock 746284923572835 @boosters`
        """
        try:
            await ctx.typing()
        except discord.Forbidden:
            return

        if not channel:
            channel = ctx.channel
        if not roles_or_members:
            roles_or_members = [ctx.guild.default_role]
        else:
            roles_or_members = roles_or_members[:10]
        succeeded = []
        cancelled = []
        failed = []
        reason = get_audit_reason(ctx.author)

        for role in roles_or_members:
            current_perms = channel.overwrites_for(role)
            if current_perms.read_messages != False and current_perms.read_messages == state:
                cancelled.append(inline(role.name))
            else:
                current_perms.update(read_messages=state)
                try:
                    await channel.set_permissions(role, overwrite=current_perms, reason=reason)
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

    @unlock.command("server")
    async def unlock_server(self, ctx: commands.Context, *roles: LockableRole):
        """
        Unlock the server.

        Provide a role if you would like to unlock it for that role.

        **Examples:**
        `[p]unlock server @members`
        """
        if not roles:
            roles = [ctx.guild.default_role]
        succeeded = []
        cancelled = []
        failed = []

        for role in roles:
            current_perms = role.permissions
            if ctx.guild.me.top_role <= role:
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

    @commands.is_owner()  # unstable, incomplete
    @unlock.command("perms")
    async def unlock_perms(
        self,
        ctx: commands.Context,
        channel: Optional[Union[LockableChannel, discord.VoiceChannel]] = None,
        state: Optional[ChannelToggle] = None,
        roles_or_members: commands.Greedy[Union[LockableRole, discord.Member]] = None,
        *permissions: str,
    ):
        """
        Set the given permissions for a role or member to `True` or `None`, depending on the given state
        """
        if not permissions:
            raise commands.BadArgument

        try:
            await ctx.typing()
        except discord.Forbidden:
            return

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
    def update_overwrite(
        ctx: commands.Context, overwrite: discord.PermissionOverwrite, permissions: dict
    ):
        base_perms = dict(iter(discord.PermissionOverwrite()))
        old_perms = copy(permissions)
        ctx.channel.permissions_for(ctx.author)
        invalid_perms = []
        valid_perms = []
        not_allowed: List[str] = []
        for perm in old_perms:
            if perm in base_perms:
                valid_perms.append(f"`{perm}`")
            else:
                invalid_perms.append(f"`{perm}`")
                del permissions[perm]
        overwrite.update(**permissions)
        if invalid_perms:
            invalid = (
                f"\nThe following permissions were invalid:\n{humanize_list(invalid_perms)}\n"
            )
            possible = humanize_list([f"`{perm}`" for perm in base_perms])
            invalid += f"Possible permissions are:\n{possible}"
        else:
            invalid = ""
        return overwrite, valid_perms, invalid, not_allowed
