import logging

import discord
from redbot.core import commands
from redbot.core.bot import Red

from .abc import MixinMeta
from .converters import StrictRole, RealEmojiConverter
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
        await self._update_cache()
        await super().initialize()

    async def _update_cache(self):
        all_guildmessage = await self.config.custom("GuildMessage").all()
        self.cache["reactroles"]["message_cache"].update(
            msg_id for guild_data in all_guildmessage.values() for msg_id in guild_data.keys()
        )

    @commands.is_owner()
    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.group(aliases=["rr"])
    async def reactrole(self, ctx: commands.Context):
        """Reaction Role management."""

    @reactrole.command(name="add")
    async def reactrole_add(
        self,
        ctx: commands.Context,
        message: discord.Message,
        emoji: RealEmojiConverter,
        role: StrictRole,
    ):
        """Add a reaction role to a message."""
        async with self.config.custom(
            "GuildMessage", ctx.guild.id, message.id
        ).reactroles() as r:
            r["react_to_roleid"][emoji if isinstance(emoji, str) else str(emoji.id)] = role.id
        if str(emoji) not in [str(emoji) for emoji in message.reactions]:
            await message.add_reaction(emoji)
        await ctx.send(f"{emoji} has been binded to {role} on {message.jump_url}")
        await self._update_cache()

    @reactrole.command(name="list")
    async def react_list(self, ctx: commands.Context):
        """View the reaction roles on this server."""
        data = await self.config.custom("GuildMessage").all()  # this is global rn
        await ctx.send(data)

    @commands.is_owner()
    @reactrole.command(hidden=True)
    async def clear(self, ctx: commands.Context):
        """Clear all ReactRole data."""
        await self.config.custom("GuildMessage").clear()
        await ctx.tick()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None or not payload.member:
            return
        if str(payload.message_id) not in self.cache["reactroles"]["message_cache"]:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild.me.guild_permissions.manage_roles:
            return

        guildmessage = await self.config.custom("GuildMessage", guild.id, payload.message_id).all()
        reacts = guildmessage["reactroles"]
        emoji_id = str(payload.emoji) if payload.emoji.is_unicode_emoji() else str(payload.emoji.id)
        role = guild.get_role(reacts["react_to_roleid"].get(emoji_id))
        if role and role not in payload.member.roles:
            await payload.member.add_roles(role, reason="Reaction role")