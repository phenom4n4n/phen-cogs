"""
MIT License

Copyright (c) 2020-2021 phenom4n4n

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

import logging
from collections import defaultdict
from colorsys import rgb_to_hsv
from typing import Optional

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import (humanize_list,
                                               humanize_timedelta, pagify,
                                               text_to_file)
from redbot.core.utils.mod import (check_permissions, get_audit_reason,
                                   is_admin_or_superior)

from .abc import MixinMeta
from .converters import FuzzyRole, StrictRole, TargeterArgs, TouchableMember
from .utils import (can_run_command, guild_roughly_chunked, humanize_roles,
                    is_allowed_by_hierarchy, is_allowed_by_role_hierarchy)

log = logging.getLogger("red.phenom4n4n.roleutils")


def targeter_cog(ctx: commands.Context):
    cog = ctx.bot.get_cog("Targeter")
    return cog is not None and hasattr(cog, "args_to_list")


def chunks(l, n):
    """
    Yield successive n-sized chunks from l.
    https://github.com/flaree/flare-cogs/blob/08b78e33ab814aa4da5422d81a5037ae3df51d4e/commandstats/commandstats.py#L16
    """
    for i in range(0, len(l), n):
        yield l[i : i + n]


class Roles(MixinMeta):
    """
    Useful role commands.
    """

    async def initialize(self):
        log.debug("Roles Initialize")
        await super().initialize()

    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    async def role(
        self, ctx: commands.Context, member: TouchableMember(False), *, role: StrictRole(False)
    ):
        """Base command for modifying roles.

        Invoking this command will add or remove the given role from the member, depending on whether they already had it."""
        if role in member.roles and await can_run_command(ctx, "role remove"):
            com = self.bot.get_command("role remove")
            await ctx.invoke(
                com,
                member=member,
                role=role,
            )
        elif role not in member.roles and await can_run_command(ctx, "role add"):
            com = self.bot.get_command("role add")
            await ctx.invoke(
                com,
                member=member,
                role=role,
            )
        else:
            await ctx.send_help()

    @commands.bot_has_permissions(embed_links=True)
    @role.command(name="info")
    async def role_info(self, ctx: commands.Context, *, role: FuzzyRole):
        """Get information about a role."""
        await ctx.send(embed=await self.get_info(role))

    async def get_info(self, role: discord.Role) -> discord.Embed:
        if guild_roughly_chunked(role.guild) is False and self.bot.intents.members:
            await role.guild.chunk()
        description = [
            f"{role.mention}",
            f"Members: {len(role.members)} | Position: {role.position}",
            f"Color: {role.color}",
            f"Hoisted: {role.hoist}",
            f"Mentionable: {role.mentionable}",
        ]
        if role.managed:
            description.append(f"Managed: {role.managed}")
        if role in await self.bot.get_mod_roles(role.guild):
            description.append(f"Mod Role: True")
        if role in await self.bot.get_admin_roles(role.guild):
            description.append(f"Admin Role: True")
        e = discord.Embed(
            color=role.color,
            title=role.name,
            description="\n".join(description),
            timestamp=role.created_at,
        )
        e.set_footer(text=role.id)
        return e

    @commands.bot_has_permissions(attach_files=True)
    @commands.admin_or_permissions(manage_roles=True)
    @role.command(name="members", aliases=["dump"])
    async def role_members(self, ctx: commands.Context, *, role: FuzzyRole):
        """Sends a list of members in a role."""
        if guild_roughly_chunked(ctx.guild) is False and self.bot.intents.members:
            await ctx.guild.chunk()
        if not role.members:
            return await ctx.send(f"**{role}** has no members.")
        members = "\n".join(f"{member} - {member.id}" for member in role.members)
        if len(members) > 2000:
            await ctx.send(file=text_to_file(members, f"members.txt"))
        else:
            await ctx.send(members)

    @staticmethod
    def get_hsv(role: discord.Role):
        return rgb_to_hsv(*role.color.to_rgb())

    @commands.bot_has_permissions(embed_links=True)
    @commands.admin_or_permissions(manage_roles=True)
    @role.command(name="colors")
    async def role_colors(self, ctx: commands.Context):
        """Sends the server's roles, ordered by color."""
        roles = defaultdict(list)
        for r in ctx.guild.roles:
            roles[str(r.color)].append(r)
        roles = dict(sorted(roles.items(), key=lambda v: self.get_hsv(v[1][0])))

        lines = [f"**{color}**\n{' '.join(r.mention for r in rs)}" for color, rs in roles.items()]
        for page in pagify("\n".join(lines)):
            e = discord.Embed(description=page)
            await ctx.send(embed=e)

    @commands.bot_has_permissions(manage_roles=True)
    @commands.admin_or_permissions(manage_roles=True)
    @role.command(name="create")
    async def role_create(
        self,
        ctx: commands.Context,
        color: Optional[discord.Color] = discord.Color.default(),
        hoist: Optional[bool] = False,
        *,
        name: str = None,
    ):
        """
        Creates a role.

        Color and whether it is hoisted can be specified.
        """
        if len(ctx.guild.roles) >= 250:
            return await ctx.send("This server has reached the maximum role limit (250).")

        role = await ctx.guild.create_role(name=name, colour=color, hoist=hoist)
        await ctx.send(f"**{role}** created!", embed=await self.get_info(role))

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command(name="color")
    async def role_color(
        self, ctx: commands.Context, role: StrictRole(check_integrated=False), color: discord.Color
    ):
        """Change a role's color."""
        await role.edit(color=color)
        await ctx.send(
            f"**{role}** color changed to **{color}**.", embed=await self.get_info(role)
        )

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command(name="name")
    async def role_name(
        self, ctx: commands.Context, role: StrictRole(check_integrated=False), *, name: str
    ):
        """Change a role's name."""
        old_name = role.name
        await role.edit(name=name)
        await ctx.send(f"Changed **{old_name}** to **{name}**.", embed=await self.get_info(role))

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command(name="add")
    async def role_add(self, ctx: commands.Context, member: TouchableMember, *, role: StrictRole):
        """Add a role to a member."""
        if role in member.roles:
            await ctx.send(
                f"**{member}** already has the role **{role}**. Maybe try removing it instead."
            )
            return
        reason = get_audit_reason(ctx.author)
        await member.add_roles(role, reason=reason)
        await ctx.send(f"Added **{role.name}** to **{member}**.")

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command(name="remove")
    async def role_remove(
        self, ctx: commands.Context, member: TouchableMember, *, role: StrictRole
    ):
        """Remove a role from a member."""
        if role not in member.roles:
            await ctx.send(
                f"**{member}** doesn't have the role **{role}**. Maybe try adding it instead."
            )
            return
        reason = get_audit_reason(ctx.author)
        await member.remove_roles(role, reason=reason)
        await ctx.send(f"Removed **{role.name}** from **{member}**.")

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command(require_var_positional=True)
    async def addmulti(self, ctx: commands.Context, role: StrictRole, *members: TouchableMember):
        """Add a role to multiple members."""
        reason = get_audit_reason(ctx.author)
        already_members = []
        success_members = []
        for member in members:
            if role not in member.roles:
                await member.add_roles(role, reason=reason)
                success_members.append(member)
            else:
                already_members.append(member)
        msg = []
        if success_members:
            msg.append(f"Added **{role}** to {humanize_roles(success_members)}.")
        if already_members:
            msg.append(f"{humanize_roles(already_members)} already had **{role}**.")
        await ctx.send("\n".join(msg))

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command(require_var_positional=True)
    async def removemulti(
        self, ctx: commands.Context, role: StrictRole, *members: TouchableMember
    ):
        """Remove a role from multiple members."""
        reason = get_audit_reason(ctx.author)
        already_members = []
        success_members = []
        for member in members:
            if role in member.roles:
                await member.remove_roles(role, reason=reason)
                success_members.append(member)
            else:
                already_members.append(member)
        msg = []
        if success_members:
            msg.append(f"Removed **{role}** from {humanize_roles(success_members)}.")
        if already_members:
            msg.append(f"{humanize_roles(already_members)} didn't have **{role}**.")
        await ctx.send("\n".join(msg))

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.group(invoke_without_command=True, require_var_positional=True)
    async def multirole(self, ctx: commands.Context, member: TouchableMember, *roles: StrictRole):
        """Add multiple roles to a member."""
        not_allowed = []
        already_added = []
        to_add = []
        for role in roles:
            allowed = await is_allowed_by_role_hierarchy(self.bot, ctx.me, ctx.author, role)
            if not allowed[0]:
                not_allowed.append(role)
            elif role in member.roles:
                already_added.append(role)
            else:
                to_add.append(role)
        reason = get_audit_reason(ctx.author)
        msg = []
        if to_add:
            await member.add_roles(*to_add, reason=reason)
            msg.append(f"Added {humanize_roles(to_add)} to **{member}**.")
        if already_added:
            msg.append(f"**{member}** already had {humanize_roles(already_added)}.")
        if not_allowed:
            msg.append(
                f"You do not have permission to assign the roles {humanize_roles(not_allowed)}."
            )
        await ctx.send("\n".join(msg))

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @multirole.command(name="remove", require_var_positional=True)
    async def multirole_remove(
        self, ctx: commands.Context, member: TouchableMember, *roles: StrictRole
    ):
        """Remove multiple roles from a member."""
        not_allowed = []
        not_added = []
        to_rm = []
        for role in roles:
            allowed = await is_allowed_by_role_hierarchy(self.bot, ctx.me, ctx.author, role)
            if not allowed[0]:
                not_allowed.append(role)
            elif role not in member.roles:
                not_added.append(role)
            else:
                to_rm.append(role)
        reason = get_audit_reason(ctx.author)
        msg = []
        if to_rm:
            await member.remove_roles(*to_rm, reason=reason)
            msg.append(f"Removed {humanize_roles(to_rm)} from **{member}**.")
        if not_added:
            msg.append(f"**{member}** didn't have {humanize_roles(not_added)}.")
        if not_allowed:
            msg.append(
                f"You do not have permission to assign the roles {humanize_roles(not_allowed)}."
            )
        await ctx.send("\n".join(msg))

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
        await self.super_massrole(
            ctx,
            [member for member in target_role.members],
            add_role,
            f"Every member of **{target_role}** has this role.",
        )

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.command(name="rin")
    async def role_rin(
        self, ctx: commands.Context, target_role: FuzzyRole, *, remove_role: StrictRole
    ):
        """Remove a role from all members of a another role."""
        await self.super_massrole(
            ctx,
            [member for member in target_role.members],
            remove_role,
            f"No one in **{target_role}** has this role.",
            False,
        )

    @commands.check(targeter_cog)
    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @role.group()
    async def target(self, ctx: commands.Context):
        """
        Modify roles using 'targeting' args.

        An explanation of Targeter and test commands to preview the members affected can be found with `[p]target`.
        """

    @target.command(name="add")
    async def target_add(self, ctx: commands.Context, role: StrictRole, *, args: TargeterArgs):
        """
        Add a role to members using targeting args.

        An explanation of Targeter and test commands to preview the members affected can be found with `[p]target`.
        """
        await self.super_massrole(
            ctx,
            args,
            role,
            f"No one was found with the given args that was eligible to recieve **{role}**.",
        )

    @target.command(name="remove")
    async def target_remove(self, ctx: commands.Context, role: StrictRole, *, args: TargeterArgs):
        """
        Remove a role from members using targeting args.

        An explanation of Targeter and test commands to preview the members affected can be found with `[p]target`.
        """
        await self.super_massrole(
            ctx,
            args,
            role,
            f"No one was found with the given args that was eligible have **{role}** removed from them.",
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
        if guild_roughly_chunked(ctx.guild) is False and self.bot.intents.members:
            await ctx.guild.chunk()
        member_list = self.get_member_list(members, role, adding)
        if not member_list:
            await ctx.send(fail_message)
            return
        verb = "add" if adding else "remove"
        word = "to" if adding else "from"
        await ctx.send(
            f"Beginning to {verb} **{role.name}** {word} **{len(member_list)}** members."
        )
        async with ctx.typing():
            result = await self.massrole(member_list, [role], get_audit_reason(ctx.author), adding)
            result_text = f"{verb.title()[:5]}ed **{role.name}** {word} **{len(result['completed'])}** members."
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
                        log.exception(f"Failed to add roles to {member}", exc_info=e)
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
                        log.exception(f"Failed to remove roles from {member}", exc_info=e)
                    else:
                        completed.append(member)
                else:
                    skipped.append(member)
        return {"completed": completed, "skipped": skipped, "failed": failed}
