import logging

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import menu, close_menu, DEFAULT_CONTROLS

from .abc import MixinMeta
from .converters import StrictRole, RealEmojiConverter
from .utils import my_role_heirarchy

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
        async with self.config.custom("GuildMessage", ctx.guild.id, message.id).reactroles() as r:
            r["react_to_roleid"][emoji if isinstance(emoji, str) else str(emoji.id)] = role.id
            r["channel"] = message.channel.id
            r["rules"] = None
        if str(emoji) not in [str(emoji) for emoji in message.reactions]:
            await message.add_reaction(emoji)
        await ctx.send(f"{emoji} has been binded to {role} on {message.jump_url}")
        await self._update_cache()

    @reactrole.command(name="list")
    async def react_list(self, ctx: commands.Context):
        """View the reaction roles on this server."""
        data = (await self.config.custom("GuildMessage").all())[str(ctx.guild.id)]
        if not data:
            return await ctx.send("There are no reaction roles set up here!")

        react_roles = []
        for index, message_data in enumerate(data.items(), start=1):
            message_id = message_data[0]
            data = message_data[1]["reactroles"]
            link = f"https://discord.com/channels/{ctx.guild.id}/{data['channel']}/{message_id}"
            reactions = [f"[Reaction Role #{index}]({link})"]
            for emoji, role in data["react_to_roleid"].items():
                role = ctx.guild.get_role(role)
                if role:
                    try:
                        emoji = int(emoji)
                    except ValueError:
                        pass
                    else:
                        emoji = self.bot.get_emoji(emoji) or emoji
                    reactions.append(f"{emoji}: {role.mention}")
                else:
                    ... # TODO make this remove the set rr if role is not found
            if len(reactions) > 1:
                react_roles.append("\n".join(reactions))
        if not react_roles:
            return await ctx.send("There are no reaction roles set up here!")

        color = await ctx.embed_color()
        description = "\n\n".join(react_roles)
        if len(description) > 2048:
            embeds = []
            pages = list(pagify(description, delims=["\n\n"], page_length=2048))
            for index, page in enumerate(pages, start=1):
                e = discord.Embed(
                    color=color,
                    description=page,
                )
                e.set_author(name="Reaction Roles", icon_url=ctx.guild.icon_url)
                e.set_footer(text=f"{index}/{len(pages)}")
                embeds.append(e)
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e = discord.Embed(
                color=color,
                description=description,
            )
            e.set_author(name="Reaction Roles", icon_url=ctx.guild.icon_url)
            emoji = self.bot.get_emoji(729917314769748019) or "❌"
            await menu(ctx, [e], {emoji: close_menu})

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
        member = payload.member
        if member.bot:
            return
        if str(payload.message_id) not in self.cache["reactroles"]["message_cache"]:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild.me.guild_permissions.manage_roles:
            return

        guildmessage = await self.config.custom("GuildMessage", guild.id, payload.message_id).all()
        reacts = guildmessage["reactroles"]
        emoji_id = (
            str(payload.emoji) if payload.emoji.is_unicode_emoji() else str(payload.emoji.id)
        )
        role = guild.get_role(reacts["react_to_roleid"].get(emoji_id)) # TODO make this remove the set rr if role is not found
        if role and my_role_heirarchy(guild, role) and role not in member.roles:
            await member.add_roles(role, reason="Reaction role")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return
        if str(payload.message_id) not in self.cache["reactroles"]["message_cache"]:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild.me.guild_permissions.manage_roles:
            return
        member = guild.get_member(payload.user_id)
        if member.bot:
            return

        guildmessage = await self.config.custom("GuildMessage", guild.id, payload.message_id).all()
        reacts = guildmessage["reactroles"]
        emoji_id = (
            str(payload.emoji) if payload.emoji.is_unicode_emoji() else str(payload.emoji.id)
        )
        role = guild.get_role(reacts["react_to_roleid"].get(emoji_id)) # TODO make this remove the set rr if role is not found
        if role and my_role_heirarchy(guild, role) and role in member.roles:
            await member.remove_roles(role, reason="Reaction role")
