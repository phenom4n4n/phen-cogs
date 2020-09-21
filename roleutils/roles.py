import asyncio
from typing import Literal
import discord
import datetime
import logging

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.mod import get_audit_reason
from redbot.core.utils.chat_formatting import humanize_timedelta

from .abc import MixinMeta
from .utils import is_allowed_by_hierarchy, is_allowed_by_role_hierarchy
from .converters import FuzzyRole

log = logging.getLogger("red.phenom4n4n.roleutils")


class Roles(MixinMeta):
    """
    Useful role commands.
    """

    @commands.group(invoke_without_command=True)
    async def role(self, ctx: commands.Context, member: discord.Member, *, role: FuzzyRole):
        """Role management."""
        if not await is_allowed_by_hierarchy(ctx.bot, ctx.author, member):
            await ctx.send(
                "You cannot do that since you aren't higher than that user in hierarchy."
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

    @commands.bot_has_permissions(embed_links=True)
    @role.command()
    async def info(self, ctx: commands.Context, *, role: FuzzyRole):
        """Get information about a role."""
        description = (
            f"{role.mention}\n"  # monkaSTEER
            f"Members: {len(role.members)} | Position: {role.position}\n"
            f"Color: {role.color}\n"
            f"Hoisted: {role.hoist}\n"
            f"Mentionable: {role.mentionable}\n"
        )
        if role.managed:
            description += f"Managed: {role.managed}"
        e = discord.Embed(
            color=role.color, title=role.name, description=description, timestamp=role.created_at
        )
        e.set_footer(text=role.id)
        await ctx.send(embed=e)

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command()
    async def add(self, ctx: commands.Context, member: discord.Member, *, role: FuzzyRole):
        """Add a role to a member."""
        if not await is_allowed_by_hierarchy(ctx.bot, ctx.author, member):
            await ctx.send(
                "You cannot do that since you aren't higher than that user in hierarchy."
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
                "You cannot do that since you aren't higher than that user in hierarchy."
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
        await self.super_massrole(ctx, ctx.guild.members, role)

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command(aliases=["removeall"])
    async def rall(self, ctx: commands.Context, role: FuzzyRole):
        """Remove a role from all members of the server."""
        allowed = is_allowed_by_role_hierarchy(self.bot, ctx.me, ctx.author, role)
        if not allowed[0]:
            await ctx.send(allowed[1])
            return
        member_list = self.get_member_list(ctx.guild.members, role, False)
        await self.super_massrole(
            ctx, ctx.guild.members, role, "No one on the server has this role.", False
        )

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command()
    async def humans(self, ctx: commands.Context, role: FuzzyRole):
        """Add a role to all humans (non-bots) in the server."""
        allowed = is_allowed_by_role_hierarchy(self.bot, ctx.me, ctx.author, role)
        if not allowed[0]:
            await ctx.send(allowed[1])
            return
        await self.super_massrole(
            ctx,
            [member for member in ctx.guild.members if not member.bot],
            role,
            "Every human in the server has this role.",
        )

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command()
    async def rhumans(self, ctx: commands.Context, role: FuzzyRole):
        """Remove a role from all humans (non-bots) in the server."""
        allowed = is_allowed_by_role_hierarchy(self.bot, ctx.me, ctx.author, role)
        if not allowed[0]:
            await ctx.send(allowed[1])
            return
        await self.super_massrole(
            ctx,
            [member for member in ctx.guild.members if not member.bot],
            role,
            "None of the humans in the server have this role.",
            False,
        )

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command()
    async def bots(self, ctx: commands.Context, role: FuzzyRole):
        """Add a role to all bots in the server."""
        allowed = is_allowed_by_role_hierarchy(self.bot, ctx.me, ctx.author, role)
        if not allowed[0]:
            await ctx.send(allowed[1])
            return
        await self.super_massrole(
            ctx,
            [member for member in ctx.guild.members if member.bot],
            role,
            "Every bot in the server has this role.",
        )

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command()
    async def rbots(self, ctx: commands.Context, role: FuzzyRole):
        """Remove a role from all bots in the server."""
        allowed = is_allowed_by_role_hierarchy(self.bot, ctx.me, ctx.author, role)
        if not allowed[0]:
            await ctx.send(allowed[1])
            return
        await self.super_massrole(
            ctx,
            [member for member in ctx.guild.members if member.bot],
            role,
            "None of the bots in the server have this role.",
            False,
        )

    async def super_massrole(
        self,
        ctx: commands.Context,
        members: list,
        role: discord.Role,
        fail_message: str = "Everyone in the server has this role.",
        adding: bool = True,
    ):
        member_list = self.get_member_list(members, role, adding)
        if not member_list:
            await ctx.send(fail_message)
            return
        verb = "add" if adding else "remove"
        word = "to" if adding else "from"
        await ctx.send(
            f"Beginning to {verb} `{role.name}` {word} **{len(member_list)}** members. "
            f"This will take {humanize_timedelta(timedelta=datetime.timedelta(seconds=len(member_list)))}."
        )
        async with ctx.typing():
            result = await self.massrole(member_list, [role], get_audit_reason(ctx.author), adding)
            result_text = f"{verb.title()[:5]}ed `{role.name}` {word} **{len(result['completed'])}** members."
            if result["skipped"]:
                result_text += (
                    f"\nSkipped {verb[:5]}ing roles for **{len(result['skipped'])}** members."
                )
            if result["failed"]:
                result_text += (
                    f"\nFailed {verb[:5]}ing roles for **{len(result['failed'])}** members."
                )
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
                        await member.remove_roles(*to_remove, reason=reason)
                    except Exception as e:
                        failed.append(member)
                        log.debug(f"Failed to add roles to {member}", exc_info=e)
                    else:
                        completed.append(member)
                else:
                    skipped.append(member)
            await asyncio.sleep(1)
        return {"completed": completed, "skipped": skipped, "failed": failed}
