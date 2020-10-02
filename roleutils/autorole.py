import discord
import logging
from typing import Optional

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

    @autorole.group(invoke_without_command=True)
    async def sticky(self, ctx: commands.Context, true_or_false: bool = None):
        """Toggle whether the bot should reapply roles on member joins and leaves."""
        pass

    #@commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        pass