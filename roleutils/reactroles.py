import logging

import discord
from redbot.core import commands
from redbot.core.bot import Red

from .abc import MixinMeta
from .converters import FuzzyRole
from .utils import is_allowed_by_role_hierarchy

log = logging.getLogger("red.phenom4n4n.roleutils.reactroles")


class ReactRoles(MixinMeta):
    """
    Reaction Roles.
    """

    def __init__(self, *_args):
        super().__init__(*_args)
        self.cache["reactroles"] = {"channel_cache": set(), "message_cache": set()}

    async def initialize(self):
        log.debug("ReactRole Initialize")
        await super().initialize()

    @commands.is_owner()
    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.group()
    async def reactrole(self, ctx: commands.Context):
        """Reaction Role management."""
        await ctx.send("This command is incomplete. Stop running it.")

    # async def add(self, ctx: commands.Context, message: discord.Message, emoji: Union[discord.Emoji, discord.PartialEmoji], role: FuzzyRole):
    #    """Add a reaction role to a message."""
    #    async with self.config.guild(ctx.guild).reactroles() as r:
    #        r[str(message.id)] = {
    #            "message": message.id,
    #            "binds": str(role.id) = {
    #                "role": role.id,
    #                "emoji": emoji.id
    #            }
    #        }

    @reactrole.command(name="list")
    async def react_list(self, ctx: commands.Context):
        """View the reaction roles on this server."""

    # @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild.me.guild_permissions.manage_roles:
            return
        data = await self.config.guild(guild).all()
        if payload.message_id not in data["reactroles"].keys():
            return
        channel = guild.get_channel(payload.channel_id)
