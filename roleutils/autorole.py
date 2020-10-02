import discord
import logging
from typing import Optional, Union

from redbot.core import commands
from redbot.core.bot import Red

from .abc import MixinMeta
from .utils import is_allowed_by_hierarchy, is_allowed_by_role_hierarchy
from .converters import FuzzyRole

log = logging.getLogger("red.phenom4n4n.roleutils.autorole")


class AutoRole(MixinMeta):
    """Manage autoroles and sticky roles."""

    @commands.is_owner()
    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.command()
    async def autorole(self, ctx: commands.Context):
        """Manage autoroles and sticky roles."""
        pass

    @autorole.command()
    async def add(self, ctx: commands.Context, *, role: FuzzyRole):
        """Add a role to be added to all new members on join."""
        pass

    @autorole.command()
    async def remove(self, ctx: commands.Context, *, role: Union[FuzzyRole, int]):
        """Remove an autorole."""
        pass

    @autorole.group()
    async def humans(self, ctx: commands.Context):
        """Manage autoroles for humans."""
        pass

    @humans.command(name="add")
    async def humans_add(self, ctx: commands.Context, *, role: FuzzyRole):
        """Add a role to be added to all new humans on join."""
        pass

    @humans.command(name="remove")
    async def humans_remove(self, ctx: commands.Context, *, role: Union[FuzzyRole, int]):
        """Remove an autorole for humans."""
        pass

    @autorole.group()
    async def bots(self, ctx: commands.Context):
        """Manage autoroles for bots."""
        pass

    @bots.command(name="add")
    async def bots_add(self, ctx: commands.Context, *, role: FuzzyRole):
        """Add a role to be added to all new bots on join."""
        pass

    @bots.command(name="remove")
    async def bots_remove(self, ctx: commands.Context, *, role: Union[FuzzyRole, int]):
        """Remove an autorole for bots."""
        pass

    @autorole.group(invoke_without_command=True)
    async def sticky(self, ctx: commands.Context, true_or_false: bool = None):
        """Toggle whether the bot should reapply roles on member joins and leaves."""
        pass

    @sticky.command(aliases=["bl"])
    async def blacklist(self, ctx: commands.Context, *, role: FuzzyRole):
        """Blacklist a role from being reapplied on joins."""
        pass

    @sticky.command(aliases=["unbl"])
    async def unblacklist(self, ctx: commands.Context, *, role: Union[FuzzyRole, int]):
        """Remove a role from the sticky blacklist."""
        pass

    #@commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        pass

    #@commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        pass