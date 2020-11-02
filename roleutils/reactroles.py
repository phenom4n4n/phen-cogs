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
        self.method = "fetch"
        self.cache["reactroles"] = {"message_cache": set()}

    async def initialize(self):
        log.debug("ReactRole Initialize")
        await self._update_cache()
        await super().initialize()

    async def _update_cache(self):
        all_guildmessage = await self.config.custom("GuildMessage").all()
        self.cache["reactroles"]["message_cache"].update(
            int(msg_id)
            for guild_data in all_guildmessage.values()
            for msg_id, msg_data in guild_data.items()
            if msg_data["reactroles"]["react_to_roleid"]
        )

    def _check_payload_to_cache(self, payload):
        return payload.message_id in self.cache["reactroles"]["message_cache"]

    def _edit_cache(
        self,
        message_id=None,
        remove=False,
    ):
        if remove:
            self.cache["reactroles"]["message_cache"].remove(message_id)
        else:
            self.cache["reactroles"]["message_cache"].add(message_id)

    async def bulk_delete_set_roles(
        self,
        guild: discord.Guild,
        message: Union[discord.Message, discord.Object],
        emoji_ids: List[str],
    ):
        async with self.config.custom("GuildMessage", guild.id, message.id).reactroles() as r:
            for emoji_id in emoji_ids:
                del r["react_to_roleid"][self.emoji_id(emoji_id)]
            if not r["react_to_roleid"]:
                # None for channel, don't assume the whole channel can stop being tracked
                self._edit_cache(message.id, True)

    def emoji_id(self, emoji: Union[discord.Emoji, str]) -> str:
        return emoji if isinstance(emoji, str) else str(emoji.id)

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
            self.cache["reactroles"]["message_cache"].update(
                await self.config.custom("GuildMessage", ctx.guild.id).all().keys()
            )
        else:
            await ctx.send("Reaction roles have been disabled in this server.")
            self.cache["reactroles"]["message_cache"].difference_update(
                await self.config.custom("GuildMessage", ctx.guild.id).all().keys()
            )

    @commands.admin_or_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True, add_reactions=True)
    @reactrole.command(name="bind")
    async def reactrole_add(
        self,
        ctx: commands.Context,
        message: discord.Message,
        emoji: RealEmojiConverter,
        role: StrictRole,
    ):
        """Bind a reaction role to an emoji on a message."""
        rules = "NORMAL"  # TODO rule arg parse converter
        emoji_id = self.emoji_id(emoji)
        async with self.config.custom("GuildMessage", ctx.guild.id, message.id).reactroles() as r:
            old_role = ctx.guild.get_role(r["react_to_roleid"].get(emoji_id))
            if old_role:
                msg = await ctx.send(
                    f"`{role}` is already binded to {emoji} on {message.jump_url}\n"
                    "Would you like to override it?"
                )
                start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
                pred = ReactionPredicate.yes_or_no(msg, ctx.author)
                try:
                    await self.bot.wait_for("reaction_add", check=pred, timeout=60)
                except asyncio.TimeoutError:
                    return await ctx.send("Bind cancelled.")

                if pred.result is not True:
                    return await ctx.send("Bind cancelled.")
                rules = r["react_to_roleid"].get("rules", "NORMAL")

            r["react_to_roleid"][self.emoji_id(emoji)] = role.id
            r["channel"] = message.channel.id
            r["rules"] = rules
        if str(emoji) not in [str(emoji) for emoji in message.reactions]:
            await message.add_reaction(emoji)
        await ctx.send(f"`{role}` has been binded to {emoji} on {message.jump_url}")

        # Add this message and channel to tracked cache
        self._edit_cache(message.id)
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

        Emoji and role groups should be seperated by a ';' and have no space.

        Example:
            - [p]reactrole create 🎃;@SpookyRole 🅱️;MemeRole #role_channel Red
        """
        if not emoji_role_groups:
            raise commands.BadArgument
        channel = channel or ctx.channel
        if color is None:
            color = await ctx.embed_color()
        if name is None:
            m = await ctx.send("What would you like the reaction role name to be?")
            try:
                msg = await self.bot.wait_for(
                    "message", check=MessagePredicate.same_context(ctx=ctx), timeout=60
                )
            except asyncio.TimeoutError:
                await delete_quietly(m)
                return await ctx.send("Reaction Role creation cancelled.")
            else:
                await delete_quietly(msg)
                await delete_quietly(m)
                name = msg.content

        description = f"React to the following roles to receive the corresponding emoji:\n"
        for (emoji, role) in emoji_role_groups:
            description += f"{emoji}: {role.mention}\n"
        e = discord.Embed(title=name[:256], color=color, description=description)
        message = await channel.send(embed=e)

        duplicates = {}
        async with self.config.custom("GuildMessage", ctx.guild.id, message.id).reactroles() as r:
            r["channel"] = message.channel.id
            r["rules"] = None
            binds = {}
            for (emoji, role) in emoji_role_groups:
                emoji_id = self.emoji_id(emoji)
                if emoji_id not in binds.keys() and role.id not in binds.values():
                    binds[emoji_id] = role.id
                    await message.add_reaction(emoji)
                else:
                    duplicates[emoji] = role
            r["react_to_roleid"] = binds
        if duplicates:
            dupes = "The following groups were duplicates and weren't added:\n"
            for emoji, role in duplicates.items():
                dupes += f"{emoji};{role}\n"
            await ctx.send(dupes)
        await ctx.tick()

        # Add this message and channel to tracked cache
        self._edit_cache(message.id)
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

        if pred.result:
            await self.config.custom("GuildMessage", ctx.guild.id, message.id).clear()
            await ctx.send("Reaction roles cleared for that message.")
            self._edit_cache(message.id, True)
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
        to_delete_message_emoji_ids = {}
        react_roles = []
        for index, (message_id, message_data) in enumerate(data.items(), start=1):
            data = message_data["reactroles"]
            channel: discord.TextChannel = guild.get_channel(data["channel"])
            if channel is None:
                # TODO: handle deleted channels
                continue
            if self.method == "fetch":
                try:
                    message: discord.Message = await channel.fetch_message(message_id)
                    # not sure how fast this would be when a server has multiple reaction roles set
                    # maybe look into dpy menus so its not fetching all the rr messages?
                    # or simply drop this since the delete listeners should handle it
                except discord.NotFound:
                    # TODO: handle deleted messages
                    continue
                link = message.jump_url
            elif self.method == "build":
                link = f"https://discord.com/channels/{ctx.guild.id}/{channel.id}/{message_id}"
            else:
                link = ""

            to_delete_emoji_ids = []

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
                    to_delete_emoji_ids.append(emoji)
            if to_delete_emoji_ids:
                to_delete_message_emoji_ids[message_id] = to_delete_emoji_ids
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
        if to_delete_message_emoji_ids:
            for message_id, ids in to_delete_message_emoji_ids.items():
                await self.bulk_delete_set_roles(ctx.guild, discord.Object(message_id), ids)

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
        role_id = reacts["react_to_roleid"].get(emoji_id)
        if not role_id:
            log.debug("No matched role id")
            return
        role = guild.get_role(role_id)  # TODO make this remove the set rr if role is not found
        if not role:
            log.debug("Role was deleted")
            await self.bulk_delete_set_roles(guild, discord.Object(payload.message_id), [emoji_id])
        if not my_role_heirarchy(guild, role):
            log.debug("Role outranks me")
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

        await self.config.custom("GuildMessage", payload.guild_id, payload.message_id).clear()
        self._edit_cache(payload.message_id, True)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        if payload.guild_id is None:
            return

        if await self.bot.cog_disabled_in_guild_raw(self.qualified_name, payload.guild_id):
            return

        for message_id in payload.message_ids:
            if message_id in self.cache["reactroles"]["message_cache"]:
                await self.config.custom("GuildMessage", payload.guild_id, message_id).clear()
                self._edit_cache(message_id, True)
