import asyncio
from typing import Literal
import discord
import datetime

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.mod import get_audit_reason
from redbot.core.utils.chat_formatting import humanize_timedelta

from .abc import MixinMeta
from .utils import is_allowed_by_hierarchy, is_allowed_by_role_hierarchy
from .converters import FuzzyRole


class Roles(MixinMeta):
    """
    Useful role commands.
    """

    @commands.group(invoke_without_command=True)
    async def role(self, ctx: commands.Context, member: discord.Member, *, role: FuzzyRole):
        """Role management."""
        if not await is_allowed_by_hierarchy(ctx.bot, ctx.author, member):
            await ctx.send(
                "You are cannot do that since you aren't higher than that user in hierarchy."
            )
            return
        allowed = is_allowed_by_role_hierarchy(self.bot, ctx.me, ctx.author, role)
        if not allowed[0]:
            await ctx.send(allowed[1])
            return
        reason = get_audit_reason(ctx.author)
        if role in member.roles:
            await member.remove_roles(*[role], reason=reason)
            await ctx.send(f"Removed `{role.name}` from `{member}`.")
        else:
            await member.add_roles(*[role], reason=reason)
            await ctx.send(f"Added `{role.name}` to `{member}`.")

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command()
    async def add(self, ctx: commands.Context, member: discord.Member, *, role: FuzzyRole):
        """Add a role to a member."""
        if not await is_allowed_by_hierarchy(ctx.bot, ctx.author, member):
            await ctx.send(
                "You are cannot do that since you aren't higher than that user in hierarchy."
            )
            return
        allowed = is_allowed_by_role_hierarchy(self.bot, ctx.me, ctx.author, role)
        if not allowed[0]:
            await ctx.send(allowed[1])
            return
        if role in member.roles:
            await ctx.send(
                f"`{member}` already has the role `{role}`. Maybe try removing it instead."
            )
            return
        reason = get_audit_reason(ctx.author)
        await member.add_roles(*[role], reason=reason)
        await ctx.send(f"Added `{role.name}` to `{member}`.")

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command()
    async def remove(self, ctx: commands.Context, member: discord.Member, *, role: FuzzyRole):
        """Remove a role from a member."""
        if not await is_allowed_by_hierarchy(ctx.bot, ctx.author, member):
            await ctx.send(
                "You are cannot do that since you aren't higher than that user in hierarchy."
            )
            return
        allowed = is_allowed_by_role_hierarchy(self.bot, ctx.me, ctx.author, role)
        if not allowed[0]:
            await ctx.send(allowed[1])
            return
        if role not in member.roles:
            await ctx.send(
                f"`{member}` doesn't have the role `{role}`. Maybe try adding it instead."
            )
            return
        reason = get_audit_reason(ctx.author)
        await member.remove_roles(*[role], reason=reason)
        await ctx.send(f"Removed `{role.name}` from `{member}`.")

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command()
    async def all(self, ctx: commands.Context, role: FuzzyRole):
        """Add a role to all members of the server."""
        allowed = is_allowed_by_role_hierarchy(self.bot, ctx.me, ctx.author, role)
        if not allowed[0]:
            await ctx.send(allowed[1])
            return
        member_list = self.get_member_list(ctx.guild.members, role)
        if not member_list:
            await ctx.send("Everyone in the server has this role.")
            return
        await ctx.send(
            f"Beginning to add `{role.name}` to **{len(member_list)}** members."
            f"This will take {humanize_timedelta(timedelta=datetime.timedelta(seconds=len(member_list)))}."
        )
        async with ctx.typing():
            result = await self.massrole(member_list, [role], get_audit_reason(ctx.author), True)
            result_text = f"Added `{role.name}` to **{len(result['completed'])}** members."
            if result["skipped"]:
                result_text += f"\nSkipped adding roles for **{len(result['skipped'])}** members."
            if result["failed"]:
                result_text += f"\nFailed adding roles for **{len(result['failed'])}** members."
        await ctx.send(result_text)

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command(aliases=["removeall"])
    async def rall(self, ctx: commands.Context, role: FuzzyRole):
        """Remove a role to all members of the server."""
        allowed = is_allowed_by_role_hierarchy(self.bot, ctx.me, ctx.author, role)
        if not allowed[0]:
            await ctx.send(allowed[1])
            return
        member_list = self.get_member_list(ctx.guild.members, role, False)
        if not member_list:
            await ctx.send("No one the server has this role.")
            return
        await ctx.send(
            f"Beginning to remove `{role.name}` from **{len(member_list)}** members."
            f"This will take {humanize_timedelta(timedelta=datetime.timedelta(seconds=len(member_list)))}."
        )
        async with ctx.typing():
            result = await self.massrole(member_list, [role], get_audit_reason(ctx.author), False)
            result_text = f"Removed `{role.name}` from **{len(result['completed'])}** members."
            if result["skipped"]:
                result_text += (
                    f"\nSkipped removing roles for **{len(result['skipped'])}** members."
                )
            if result["failed"]:
                result_text += f"\nFailed removing roles for **{len(result['failed'])}** members."
        await ctx.send(result_text)

    def get_member_list(self, members: list, role: discord.Role, adding: bool = True):
        if adding:
            members = [member for member in members if role not in member.roles]
        else:
            members = [member for member in members if role in member.roles]
        return members

    async def massrole(self, members: list, roles: list, reason: str, adding: bool = True):
        completed = []
        skipped = []
        failed = []
        for member in members:
            if adding:
                to_add = [role for role in roles if role not in member.roles]
                if to_add:
                    try:
                        await member.add_roles(*to_add, reason=reason)
                    except:
                        failed.append(member)
                    else:
                        completed.append(member)
                else:
                    skipped.append(member)
            else:
                to_remove = [role for role in roles if role in member.roles]
                if to_remove:
                    try:
                        await member.remove_roles(*to_remove, reason)
                    except:
                        failed.append(member)
                    else:
                        completed.append(member)
                else:
                    skipped.append(member)
            await asyncio.sleep(1)
        return {"completed": completed, "skipped": skipped, "failed": failed}
