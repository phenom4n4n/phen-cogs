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
from typing import Union

import discord
from redbot.core import commands
from redbot.core.bot import Red

from .abc import MixinMeta
from .converters import FuzzyRole
from .utils import is_allowed_by_hierarchy, is_allowed_by_role_hierarchy

log = logging.getLogger("red.phenom4n4n.roleutils.autorole")


class AutoRole(MixinMeta):
    """Manage autoroles and sticky roles."""

    async def initialize(self):
        log.debug("AutoRole Initialize")
        await super().initialize()

    @commands.is_owner()
    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.group(name="autorole")
    async def _autorole(self, ctx: commands.Context):
        """Manage autoroles and sticky roles."""

    @_autorole.command()
    async def add(self, ctx: commands.Context, *, role: FuzzyRole):
        """Add a role to be added to all new members on join."""

    @_autorole.command()
    async def remove(self, ctx: commands.Context, *, role: Union[FuzzyRole, int]):
        """Remove an autorole."""

    @_autorole.group(name="humans")
    async def _humans(self, ctx: commands.Context):
        """Manage autoroles for humans."""

    @_humans.command(name="add")
    async def humans_add(self, ctx: commands.Context, *, role: FuzzyRole):
        """Add a role to be added to all new humans on join."""

    @_humans.command(name="remove")
    async def humans_remove(self, ctx: commands.Context, *, role: Union[FuzzyRole, int]):
        """Remove an autorole for humans."""

    @_autorole.group(name="bots")
    async def _bots(self, ctx: commands.Context):
        """Manage autoroles for bots."""

    @_bots.command(name="add")
    async def bots_add(self, ctx: commands.Context, *, role: FuzzyRole):
        """Add a role to be added to all new bots on join."""

    @_bots.command(name="remove")
    async def bots_remove(self, ctx: commands.Context, *, role: Union[FuzzyRole, int]):
        """Remove an autorole for bots."""

    @_autorole.group(invoke_without_command=True, name="sticky")
    async def _sticky(self, ctx: commands.Context, true_or_false: bool = None):
        """Toggle whether the bot should reapply roles on member joins and leaves."""

    @_sticky.command(aliases=["bl"])
    async def blacklist(self, ctx: commands.Context, *, role: FuzzyRole):
        """Blacklist a role from being reapplied on joins."""

    @_sticky.command(aliases=["unbl"])
    async def unblacklist(self, ctx: commands.Context, *, role: Union[FuzzyRole, int]):
        """Remove a role from the sticky blacklist."""

    # @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        pass

    # @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        pass
