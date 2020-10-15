import asyncio
import datetime
import logging
from typing import Optional

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import (humanize_list,
                                               humanize_timedelta,
                                               text_to_file)
from redbot.core.utils.mod import get_audit_reason

from .abc import MixinMeta
from .converters import FuzzyRole, StrictRole
from .utils import (humanize_roles, is_allowed_by_hierarchy,
                    is_allowed_by_role_hierarchy)

log = logging.getLogger("red.phenom4n4n.roleutils")


class Roles(MixinMeta):
    """
    Useful role commands.
    """

    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    async def role(self, ctx: commands.Context, member: discord.Member, *, role: StrictRole):
        """Role management.

        Invoking this command will add or remove the given role from the member, depending on whether they already had it."""
        if not await is_allowed_by_hierarchy(ctx.bot, ctx.author, member):
            await ctx.send(
                "You cannot do that since you aren't higher than that user in hierarchy."
            )
            return
        reason = get_audit_reason(ctx.author)
        if role in member.roles:
            await member.remove_roles(*[role], reason=reason)
            await ctx.send(f"Removed `{role.name}` from **{member}**.")
        else:
            await member.add_roles(*[role], reason=reason)
            await ctx.send(f"Added `{role.name}` to **{member}**.")

    @commands.bot_has_permissions(embed_links=True)
    @role.command()
    async def info(self, ctx: commands.Context, *, role: FuzzyRole):
        """Get information about a role."""
        await ctx.send(embed=self.get_info(role))

    @commands.bot_has_permissions(attach_files=True)
    @commands.admin_or_permissions(manage_roles=True)
    @role.command(aliases=["dump"])
    async def members(self, ctx: commands.Context, *, role: FuzzyRole):
        """Sends a list of members in a role."""
        members = "\n".join([f"{member} - {member.id}" for member in role.members])
        if len(members) > 2000:
            await ctx.send(file=text_to_file(members, f"members.txt"))
        else:
            await ctx.send(members)

    @commands.bot_has_permissions(manage_roles=True)
    @commands.admin_or_permissions(manage_roles=True)
    @role.command()
    async def create(
        self,
        ctx: commands.Context,
        color: Optional[discord.Color] = None,
        hoist: Optional[bool] = False,
        *,
        name: str = None,
    ):
        """Creates a role.

        Color and whether it is hoisted can be specified."""
        color = color or discord.Color.default()
        role = await ctx.guild.create_role(name=name, colour=color, hoist=hoist)
        await ctx.send(f"**{role}** created!", embed=self.get_info(role))

    @staticmethod
    def get_info(role: discord.Role) -> discord.Embed:
        description = (
            f"{role.mention}\n"
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
        return e

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command()
    async def add(self, ctx: commands.Context, member: discord.Member, *, role: StrictRole):
        """Add a role to a member."""
        if not await is_allowed_by_hierarchy(ctx.bot, ctx.author, member):
            await ctx.send(
                "You cannot do that since you aren't higher than that user in hierarchy."
            )
            return
        if role in member.roles:
            await ctx.send(
                f"**{member}** already has the role `{role}`. Maybe try removing it instead."
            )
            return
        reason = get_audit_reason(ctx.author)
        await member.add_roles(*[role], reason=reason)
        await ctx.send(f"Added `{role.name}` to **{member}**.")

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command()
    async def remove(self, ctx: commands.Context, member: discord.Member, *, role: StrictRole):
        """Remove a role from a member."""
        if not await is_allowed_by_hierarchy(ctx.bot, ctx.author, member):
            await ctx.send(
                "You cannot do that since you aren't higher than that user in hierarchy."
            )
            return
        if role not in member.roles:
            await ctx.send(
                f"**{member}** doesn't have the role `{role}`. Maybe try adding it instead."
            )
            return
        reason = get_audit_reason(ctx.author)
        await member.remove_roles(*[role], reason=reason)
        await ctx.send(f"Removed `{role.name}` from **{member}**.")

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.group(invoke_without_command=True)
    async def multirole(self, ctx: commands.Context, member: discord.Member, *roles: StrictRole):
        """Add multiple roles to a member."""
        if not await is_allowed_by_hierarchy(ctx.bot, ctx.author, member):
            await ctx.send(
                "You cannot do that since you aren't higher than that user in hierarchy."
            )
            return
        not_allowed = []
        already_added = []
        to_add = []
        for role in roles:
            allowed = is_allowed_by_role_hierarchy(self.bot, ctx.me, ctx.author, role)
            if not allowed[0]:
                not_allowed.append(role)
            elif role in member.roles:
                already_added.append(role)
            else:
                to_add.append(role)
        reason = get_audit_reason(ctx.author)
        msg = ""
        if to_add:
            await member.add_roles(*to_add, reason=reason)
            msg += f"Added {humanize_roles(to_add)} to {member}."
        if already_added:
            msg += f"\n**{member}** already had {humanize_roles(already_added)}."
        if not_allowed:
            msg += (
                f"\nYou do not have permission to assign the roles {humanize_roles(not_allowed)}."
            )
        if msg:
            await ctx.send(msg)

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @multirole.command(name="remove")
    async def multirole_remove(
        self, ctx: commands.Context, member: discord.Member, *roles: StrictRole
    ):
        """Remove multiple roles from a member."""
        if not await is_allowed_by_hierarchy(ctx.bot, ctx.author, member):
            await ctx.send(
                "You cannot do that since you aren't higher than that user in hierarchy."
            )
            return
        not_allowed = []
        not_added = []
        to_rm = []
        for role in roles:
            allowed = is_allowed_by_role_hierarchy(self.bot, ctx.me, ctx.author, role)
            if not allowed[0]:
                not_allowed.append(role)
            elif role not in member.roles:
                not_added.append(role)
            else:
                to_rm.append(role)
        reason = get_audit_reason(ctx.author)
        msg = ""
        if to_rm:
            await member.remove_roles(*to_rm, reason=reason)
            msg += f"Removed {humanize_roles(to_rm)} from {member}."
        if not_added:
            msg += f"\n**{member}** didn't have {humanize_roles(not_added)}."
        if not_allowed:
            msg += (
                f"\nYou do not have permission to assign the roles {humanize_roles(not_allowed)}."
            )
        if msg:
            await ctx.send(msg)

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command()
    async def all(self, ctx: commands.Context, *, role: StrictRole):
        """Add a role to all members of the server."""
        await self.super_massrole(ctx, ctx.guild.members, role)

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command(aliases=["removeall"])
    async def rall(self, ctx: commands.Context, *, role: StrictRole):
        """Remove a role from all members of the server."""
        member_list = self.get_member_list(ctx.guild.members, role, False)
        await self.super_massrole(
            ctx, member_list, role, "No one on the server has this role.", False
        )

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command()
    async def humans(self, ctx: commands.Context, *, role: StrictRole):
        """Add a role to all humans (non-bots) in the server."""
        await self.super_massrole(
            ctx,
            [member for member in ctx.guild.members if not member.bot],
            role,
            "Every human in the server has this role.",
        )

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command()
    async def rhumans(self, ctx: commands.Context, *, role: StrictRole):
        """Remove a role from all humans (non-bots) in the server."""
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
    async def bots(self, ctx: commands.Context, *, role: StrictRole):
        """Add a role to all bots in the server."""
        await self.super_massrole(
            ctx,
            [member for member in ctx.guild.members if member.bot],
            role,
            "Every bot in the server has this role.",
        )

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command()
    async def rbots(self, ctx: commands.Context, *, role: StrictRole):
        """Remove a role from all bots in the server."""
        await self.super_massrole(
            ctx,
            [member for member in ctx.guild.members if member.bot],
            role,
            "None of the bots in the server have this role.",
            False,
        )

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command(name="in")
    async def role_in(
        self, ctx: commands.Context, target_role: FuzzyRole, *, add_role: StrictRole
    ):
        """Add a role to all members of a another role."""
        allowed = is_allowed_by_role_hierarchy(self.bot, ctx.me, ctx.author, add_role)
        if not allowed[0]:
            await ctx.send(allowed[1])
            return
        await self.super_massrole(
            ctx,
            [member for member in target_role.members],
            add_role,
            f"Every member of `{target_role}` has this role.",
        )

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command(name="rin")
    async def role_rin(
        self, ctx: commands.Context, target_role: FuzzyRole, *, remove_role: StrictRole
    ):
        """Remove a role all members of a another role."""
        allowed = is_allowed_by_role_hierarchy(self.bot, ctx.me, ctx.author, remove_role)
        if not allowed[0]:
            await ctx.send(allowed[1])
            return
        await self.super_massrole(
            ctx,
            [member for member in target_role.members],
            remove_role,
            f"No one in `{target_role}` has this role.",
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
            f"This will take around {humanize_timedelta(timedelta=datetime.timedelta(seconds=len(member_list) * 0.75))}."
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
                    except Exception as e:
                        failed.append(member)
                        log.debug(f"Failed to add roles to {member}\n{e}")
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
                        log.debug(f"Failed to remove roles from {member}\n{e}")
                    else:
                        completed.append(member)
                else:
                    skipped.append(member)
            await asyncio.sleep(0.5)
        return {"completed": completed, "skipped": skipped, "failed": failed}
