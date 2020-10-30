import logging
from typing import List, Union, Optional
import asyncio

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.predicates import ReactionPredicate, MessagePredicate
from redbot.core.utils.menus import menu, close_menu, DEFAULT_CONTROLS, start_adding_reactions

from .abc import MixinMeta
from .converters import StrictRole, RealEmojiConverter, ObjectConverter, EmojiRole
from .utils import my_role_heirarchy, delete_quietly

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
        all_guilds = await self.config.all_guilds()  # This won't return default values
        all_guildmessage = await self.config.custom("GuildMessage").all()
        self.cache["reactroles"]["message_cache"].update(
            int(msg_id) for guild_data in all_guildmessage.values() for msg_id in guild_data.keys()
        )
        log.debug(all_guilds)
        self.cache["reactroles"]["channel_cache"].update(
            int(chnl_id)
            for guild_data in all_guilds.values()
            for chnl_id in guild_data["reactroles"].get("channels", [])
            if guild_data["reactroles"].get(
                "enabled", False
            )  # Unsure if we should only cache enabled
        )

    def _check_payload_to_cache(self, payload):
        return (
            payload.channel_id in self.cache["reactroles"]["channel_cache"]
            and payload.message_id in self.cache["reactroles"]["message_cache"]
        )

    def _edit_cache(
        self,
        message_id,
        channel_id,
        remove=False,
    ):
        if not remove:
            self.cache["reactroles"]["message_cache"].add(message_id)
            self.cache["reactroles"]["channel_cache"].add(channel_id)
        else:
            self.cache["reactroles"]["message_cache"].remove(message_id)
            # channel = message.channel if hasattr(message, "channel") else channel
            # channel = getattr(message, "channel", False) or channel
            # if channel:  # for when the message/channel objects are unknown/deleted
            self.cache["reactroles"]["channel_cache"].remove(channel_id)

    async def bulk_delete_set_roles(
        self,
        guild: discord.Guild,
        message_id: Union[discord.Message, discord.Object],
        emoji_ids: List[int],
    ):
        ...  # TODO delete deleted roles from message id using emoji ids
        # if there are no roles left, clear the rr altogether

    def emoji_id(self, emoji: Union[discord.Emoji, str]) -> str:
        return emoji if isinstance(emoji, str) else str(emoji.id)

    @commands.command()
    async def test(self, ctx: commands.Context, emojirole: EmojiRole):
        await ctx.send(emojirole)

    @commands.is_owner()
    @commands.group(aliases=["rr"])
    async def reactrole(self, ctx: commands.Context):
        """Base command for Reaction Role management."""

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @reactrole.command()
    async def enable(self, ctx: commands.Context, true_or_false: bool = None):
        """Toggle reaction roles on or off."""
        target_state = (
            true_or_false
            if true_or_false is not None
            else not (await self.config.guild(ctx.guild).reactroles.enabled())
        )
        await self.config.guild(ctx.guild).reactroles.enabled.set(target_state)
        if target_state:
            await ctx.send("Reaction roles have been enabled in this server.")
            self.cache["reactroles"]["channel_cache"].update(
                await self.config.guild(ctx.guild).reactroles.channels()
            )
        else:
            await ctx.send("Reaction roles have been disabled in this server.")
            self.cache["reactroles"]["channel_cache"].difference_update(
                await self.config.guild(ctx.guild).reactroles.channels()
            )

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    @reactrole.command(name="add")
    async def reactrole_add(
        self,
        ctx: commands.Context,
        message: discord.Message,
        emoji: RealEmojiConverter,
        role: StrictRole,
    ):
        """Add a reaction role to a message."""
        # TODO warning if this emoji is already binded
        async with self.config.custom("GuildMessage", ctx.guild.id, message.id).reactroles() as r:
            r["react_to_roleid"][self.emoji_id(emoji)] = role.id
            r["channel"] = message.channel.id
            r["rules"] = None
        if str(emoji) not in [str(emoji) for emoji in message.reactions]:
            await message.add_reaction(emoji)
        await ctx.send(f"{emoji} has been binded to {role} on {message.jump_url}")

        # Add this message and channel to tracked cache
        self._edit_cache(message.id, message.channel.id)
        async with self.config.guild(ctx.guild).reactroles.channels() as ch:
            if message.channel.id not in ch:
                ch.append(message.channel.id)

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True, embed_links=True)
    @reactrole.command(name="create")
    async def reactrole_create(
        self,
        ctx: commands.Context,
        emoji_role_groups: commands.Greedy[EmojiRole],
        channel: Optional[discord.TextChannel] = None,
        color: Optional[discord.Color] = None,
        *,
        name: str = None,
    ):
        """Create a reaction role.

        Emoji and role groups should be seperated by a ';' and have no space."""
        if not emoji_role_groups:
            raise commands.BadArgument
        channel = channel or ctx.channel
        color = await ctx.embed_color()
        if name is None:
            await ctx.send("What would you like the reaction role name to be?")
            try:
                msg = await self.bot.wait_for(
                    "message", check=MessagePredicate.same_context(ctx=ctx), timeout=60
                )
            except asyncio.TimeoutError:
                return await ctx.send("Reaction Role creation cancelled.")
            else:
                await delete_quietly(msg)
                name = msg.content

        description = f"React to the following roles to receive the corresponding emoji:\n"
        for group in emoji_role_groups:
            description += f"{group['emoji']}: {group['role'].mention}\n"
        e = discord.Embed(title=name[:256], color=color, description=description)
        message = await channel.send(embed=e)

        duplicates = {}
        async with self.config.custom("GuildMessage", ctx.guild.id, message.id).reactroles() as r:
            r["channel"] = message.channel.id
            r["rules"] = None
            binds = {}
            for group in emoji_role_groups:
                emoji_id = self.emoji_id(group["emoji"])
                if emoji_id not in binds.keys() and group["role"].id not in binds.values():
                    binds[emoji_id] = group["role"].id
                    await message.add_reaction(group["emoji"])
                else:
                    duplicates[group["emoji"]] = group["role"]
            r["react_to_roleid"] = binds
        if duplicates:
            dupes = "The following groups were duplicates and weren't added:\n"
            for emoji, role in duplicates.items():
                dupes += f"{emoji};{role}\n"
            await ctx.send(dupes)
        await ctx.tick()

        # Add this message and channel to tracked cache
        self._edit_cache(message.id, message.channel.id)
        async with self.config.guild(ctx.guild).reactroles.channels() as ch:
            if message.channel.id not in ch:
                ch.append(message.channel.id)

    @commands.admin_or_permissions(manage_roles=True)
    @reactrole.group(name="delete", aliases=["remove"], invoke_without_command=True)
    async def reactrole_delete(
        self,
        ctx: commands.Context,
        message: Union[discord.Message, ObjectConverter],
    ):
        """Delete an entire reaction role for a message."""
        message_data = await self.config.custom("GuildMessage", ctx.guild.id, message.id).all()
        if not message_data["reactroles"]["react_to_roleid"]:
            return await ctx.send("There are no reaction roles set up for that message.")

        msg = await ctx.send(
            "Are you sure you want to remove all reaction roles for that message?"
        )
        start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
        pred = ReactionPredicate.yes_or_no(msg, ctx.author)
        try:
            await self.bot.wait_for("reaction_add", check=pred, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send("Action cancelled.")

        if pred.result is True:
            await self.config.custom("GuildMessage", ctx.guild.id, message.id).clear()
            await ctx.send("Reaction roles cleared for that message.")
            self._edit_cache(message.id, message.channel.id, True)
        else:
            await ctx.send("Action cancelled.")

    @reactrole_delete.command(name="bind")
    async def delete_bind(
        self,
        ctx: commands.Context,
        message: Union[discord.Message, ObjectConverter],
        emoji: Union[RealEmojiConverter, ObjectConverter],
    ):
        """Delete an emoji-role bind for a reaction role."""
        async with self.config.custom("GuildMessage", ctx.guild.id, message.id).reactroles() as r:
            try:
                del r["react_to_roleid"][emoji if isinstance(emoji, str) else str(emoji.id)]
            except KeyError:
                return await ctx.send("That wasn't a valid emoji for that message.")
        await ctx.send(f"That emoji role bind was deleted.")

    @commands.admin_or_permissions(manage_roles=True)
    @reactrole.command(name="list")
    async def react_list(self, ctx: commands.Context):
        """View the reaction roles on this server."""
        data = await self.config.custom("GuildMessage", ctx.guild.id).all()
        if not data:
            return await ctx.send("There are no reaction roles set up here!")
        guild: discord.Guild = ctx.guild
        react_roles = []
        for index, (message_id, message_data) in enumerate(data.items(), start=1):
            data = message_data["reactroles"]
            channel: discord.TextChannel = guild.get_channel(data["channel"])
            if channel is None:
                # TODO: handle deleted channels
                continue
            try:
                message: discord.Message = await channel.fetch_message(message_id)
            except discord.NotFound:
                # TODO: handle deleted messages
                continue
            link = message.jump_url
            # link = f"https://discord.com/channels/{ctx.guild.id}/{data['channel']}/{message_id}"
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
                    ...  # TODO make this remove the set rr if role is not found
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
        msg = await ctx.send("Are you sure you want to clear all reaction role data?")
        start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
        pred = ReactionPredicate.yes_or_no(msg, ctx.author)
        try:
            await self.bot.wait_for("reaction_add", check=pred, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send("Action cancelled.")

        if pred.result is True:
            await self.config.custom("GuildMessage").clear()
            await ctx.send("Data cleared.")
            await self._update_cache()
        else:
            await ctx.send("Action cancelled.")

    @commands.Cog.listener("on_raw_reaction_add")
    @commands.Cog.listener("on_raw_reaction_remove")
    async def on_raw_reaction_add_or_remove(self, payload: discord.RawReactionActionEvent):
        log.debug("Begin reaction listener")
        if payload.guild_id is None:
            log.debug("Not functioning in a guild")
            return

        # TODO add in listeners
        if not self._check_payload_to_cache(payload):
            log.debug("Not cached")
            return

        if await self.bot.cog_disabled_in_guild_raw(self.qualified_name, payload.guild_id):
            return

        guild = self.bot.get_guild(payload.guild_id)
        if payload.event_type == "REACTION_ADD":
            member = payload.member
        else:
            member = guild.get_member(payload.user_id)

        if member is None or member.bot:
            log.debug("Failed to get member or member is a bot")
            return
        if not guild.me.guild_permissions.manage_roles:
            log.debug("No permissions to manage roles")
            return

        reacts = await self.config.custom(
            "GuildMessage", guild.id, payload.message_id
        ).reactroles.all()
        emoji_id = (
            str(payload.emoji) if payload.emoji.is_unicode_emoji() else str(payload.emoji.id)
        )
        role = guild.get_role(
            reacts["react_to_roleid"].get(emoji_id)
        )  # TODO make this remove the set rr if role is not found
        if not role or not my_role_heirarchy(guild, role):
            log.debug("Failed to get role, or role outranks me")
            return

        if payload.event_type == "REACTION_ADD":
            if role not in member.roles:
                await member.add_roles(role, reason="Reaction role")
        else:
            if role in member.roles:
                await member.remove_roles(role, reason="Reaction role")

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if payload.guild_id is None:
            return

        if not self._check_payload_to_cache(payload):
            return

        if await self.bot.cog_disabled_in_guild_raw(self.qualified_name, payload.guild_id):
            return

        # message, guild = discord.Object(payload.message_id), discord.Object(payload.guild_id)
        await self.config.custom("GuildMessage", payload.guild_id, payload.message_id).clear()
        self._edit_cache(payload.message_id, payload.channel_id, True)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        ...

    # @commands.Cog.listener()
    # async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
    #     if payload.guild_id is None:
    #         return
    #     # TODO add channel caching here and in listeners
    #     if str(payload.message_id) not in self.cache["reactroles"]["message_cache"]:
    #         return
    #     guild = self.bot.get_guild(payload.guild_id)
    #     if not guild.me.guild_permissions.manage_roles:
    #         return
    #     member = guild.get_member(payload.user_id)
    #     if member.bot:
    #         return
    #
    #     guildmessage = await self.config.custom("GuildMessage", guild.id, payload.message_id).all()
    #     reacts = guildmessage["reactroles"]
    #     emoji_id = (
    #         str(payload.emoji) if payload.emoji.is_unicode_emoji() else str(payload.emoji.id)
    #     )
    #     role = guild.get_role(
    #         reacts["react_to_roleid"].get(emoji_id)
    #     )  # TODO make this remove the set rr if role is not found
    #     if role and my_role_heirarchy(guild, role) and role in member.roles:
    #         await member.remove_roles(role, reason="Reaction role")
