import asyncio
from copy import copy
from typing import List

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_list, inline, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils.predicates import MessagePredicate

from .abc import MixinMeta
from .converters import SLASH_NAME, TagConverter, TagName, TagScriptConverter
from .errors import (BlacklistCheckFailure, MissingTagPermissions,
                     RequireCheckFailure, WhitelistCheckFailure)
from .http import SlashHTTP
from .models import SlashOptionType
from .objects import (FakeMessage, SlashCommand, SlashContext, SlashOption,
                      SlashTag)
from .utils import dev_check


class Commands(MixinMeta):
    @commands.guild_only()
    @commands.group(aliases=["st"])
    async def slashtag(self, ctx: commands.Context):
        """
        Slash Tag management with TagScript.

        These commands use TagScriptEngine. [This site](https://phen-cogs.readthedocs.io/en/latest/index.html) has documentation on how to use TagScript blocks.
        """

    @commands.mod_or_permissions(manage_guild=True)
    @slashtag.command(name="add", aliases=["create", "+"])
    async def slashtag_add(
        self, ctx: commands.Context, tag_name: TagName, *, tagscript: TagScriptConverter
    ):
        """
        Add a slash tag with TagScript.

        [Slash tag usage guide](https://phen-cogs.readthedocs.io/en/latest/blocks.html#usage)
        """
        options: List[SlashOption] = []

        try:
            description = await self.send_and_query_response(
                ctx,
                "What should the tag description to be? (maximum 100 characters)",
                pred=MessagePredicate.length_less(101, ctx),
            )
        except asyncio.TimeoutError:
            return await ctx.send("Tag addition timed out.")

        pred = MessagePredicate.yes_or_no(ctx)
        try:
            await self.send_and_query_response(
                ctx, "Would you like to add arguments to this tag? (Y/n)", pred
            )
        except asyncio.TimeoutError:
            await ctx.send("Query timed out, not adding arguments.")
        else:
            if pred.result is True:
                await self.get_options(ctx, options)

        command = SlashCommand(
            self, name=tag_name, description=description, guild_id=ctx.guild.id, options=options
        )
        try:
            await command.register()
        except discord.Forbidden:
            text = (
                "Looks like I don't have permission to add Slash Commands here. Reinvite me "
                "with this invite link and try again: <https://discordapp.com/oauth2/authorize"
                f"?client_id={self.bot.user.id}&scope=bot%20applications.commands>"
            )
            return await ctx.send(text)

        tag = SlashTag(
            self,
            tagscript,
            guild_id=ctx.guild.id,
            author_id=ctx.author.id,
            command=command,
        )
        self.command_cache[tag.command.id] = tag.command
        await ctx.send(await tag.initialize())

    async def get_options(
        self, ctx: commands.Context, options: List[SlashOption]
    ) -> List[SlashOption]:
        added_required = False
        for i in range(1, 11):
            try:
                option = await self.get_option(ctx, added_required=added_required)
                if not option.required:
                    added_required = True
            except asyncio.TimeoutError:
                await ctx.send("Adding this argument timed out.", delete_after=15)
                break

            options.append(option)
            if i == 10:
                break

            pred = MessagePredicate.yes_or_no(ctx)
            try:
                await self.send_and_query_response(
                    ctx, "Would you like to add another argument? (Y/n)", pred
                )
            except asyncio.TimeoutError:
                await ctx.send("Query timed out, not adding additional arguments.")
                break

            if pred.result is False:
                break
        return options

    async def send_and_query_response(
        self,
        ctx: commands.Context,
        query: str,
        pred: MessagePredicate = None,
        *,
        timeout: int = 60,
    ) -> str:
        if pred is None:
            pred = MessagePredicate.same_context(ctx)
        ask = await ctx.send(query)
        try:
            message = await self.bot.wait_for("message", check=pred, timeout=timeout)
        except asyncio.TimeoutError:
            await self.delete_quietly(ask)
            raise
        await self.delete_quietly(ask)
        await self.delete_quietly(message)
        return message.content

    async def get_option(
        self, ctx: commands.Context, *, added_required: bool = False
    ) -> SlashOption:
        name_desc = (
            "What should the argument name be?\n"
            "Slash argument names may not exceed 32 characters and can only contain characters "
            "that are alphanumeric or '_' or '-'."
        )
        name_pred = MessagePredicate.regex(SLASH_NAME, ctx)
        await self.send_and_query_response(ctx, name_desc, name_pred)
        title = name_pred.result.group(1)
        description = await self.send_and_query_response(
            ctx,
            "What should the argument description be? (maximum 100 characters)",
            MessagePredicate.length_less(101, ctx),
        )

        valid_option_types = [
            name.lower()
            for name in SlashOptionType.__members__.keys()
            if not name.startswith("SUB")
        ]

        option_query = [
            "What should the argument type be?",
            f"Valid option types: {humanize_list([inline(n) for n in valid_option_types])}",
            "(select `string` if you don't understand)",
        ]
        option_type = await self.send_and_query_response(
            ctx,
            "\n".join(option_query),
            MessagePredicate.lower_contained_in(valid_option_types, ctx),
        )
        option_type = SlashOptionType[option_type.upper()]

        if not added_required:
            pred = MessagePredicate.yes_or_no(ctx)
            await self.send_and_query_response(
                ctx,
                "Is this argument required? (Y/n)\n*Keep in mind that if you choose to make this argument optional, all following arguments must also be optional.*",
                pred,
            )
            required = pred.result
        else:
            await ctx.send(
                "This argument was automatically made optional as the previous one was optional.",
                delete_after=15,
            )
            required = False

        return SlashOption(
            name=title, description=description, option_type=option_type, required=required
        )

    @commands.mod_or_permissions(manage_guild=True)
    @slashtag.group(name="edit", aliases=["e"])
    async def slashtag_edit(self, ctx: commands.Context):
        """Edit a slash tag."""

    @slashtag_edit.command(name="tagscript")
    async def slashtag_edit_tagscript(
        self, ctx: commands.Context, tag: TagConverter, *, tagscript: TagScriptConverter
    ):
        """Edit a slash tag's TagScript."""
        await ctx.send(tag.edit_tagscript(tagscript))

    @slashtag_edit.command(name="name")
    async def slashtag_edit_name(self, ctx: commands.Context, tag: TagConverter, name: TagName):
        """Edit a slash tag's name."""
        await ctx.send(tag.edit_name(name))

    @slashtag_edit.command(name="description")
    async def slashtag_edit_description(
        self, ctx: commands.Context, tag: TagConverter, *, description: str
    ):
        """Edit a slash tag's description."""
        await ctx.send(await tag.edit_description(description))

    @slashtag_edit.command(name="arguments")
    async def slashtag_edit_arguments(self, ctx: commands.Context, tag: TagConverter):
        """Edit a slash tag's arguments."""
        await tag.edit_options(ctx)

    @commands.mod_or_permissions(manage_guild=True)
    @slashtag.command(name="remove", aliases=["delete", "-"])
    async def slashtag_remove(self, ctx: commands.Context, tag: TagConverter):
        """Delete a slash tag."""
        await ctx.send(await tag.delete())

    @slashtag.command(name="info")
    async def slashtag_info(self, ctx: commands.Context, tag: TagConverter):
        """Get info about a slash tag that is stored on this server."""
        await tag.send_info(ctx)

    @slashtag.command(name="raw")
    async def slashtag_raw(self, ctx: commands.Context, tag: TagConverter):
        """Get a slash tag's raw content."""
        await tag.send_raw_tagscript(ctx)

    @staticmethod
    def format_tagscript(tag: SlashTag, limit: int = 60) -> str:
        prefix = f"`{tag.name}` - "
        limit -= len(prefix)
        tagscript = tag.tagscript
        if len(tagscript) > limit - 3:
            tagscript = tagscript[:limit] + "..."
        tagscript = tagscript.replace("\n", " ")
        return f"{prefix}{discord.utils.escape_markdown(tagscript)}"

    @slashtag.command(name="list")
    async def slashtag_list(self, ctx: commands.Context):
        """View stored slash tags."""
        tags = self.guild_tag_cache[ctx.guild.id]
        if not tags:
            return await ctx.send("There are no slash tags on this server.")
        description = [self.format_tagscript(tag) for tag in tags.values()]

        description = "\n".join(description)

        e = discord.Embed(color=await ctx.embed_color())
        e.set_author(name="Stored Slash Tags", icon_url=ctx.guild.icon_url)

        embeds = []
        pages = list(pagify(description))
        for index, page in enumerate(pages, 1):
            embed = e.copy()
            embed.description = page
            embed.set_footer(text=f"{index}/{len(pages)} | {len(tags)} slash tags")
            embeds.append(embed)
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @commands.is_owner()
    @slashtag.command(name="clear", hidden=True)
    async def slashtag_clear(self, ctx: commands.Context):
        """Clear all slash tags for this server."""
        pred = MessagePredicate.yes_or_no(ctx)
        try:
            await self.send_and_query_response(
                ctx, "Are you sure you want to delete all slash tags on this server? (Y/n)", pred
            )
        except asyncio.TimeoutError:
            return await ctx.send("Timed out, not deleting slash tags.")
        if not pred.result:
            return await ctx.send("Ok, not deleting slash tags.")
        guild: discord.Guild = ctx.guild
        await self.http.put_guild_slash_commands(guild.id, [])
        for tag in copy(self.guild_tag_cache[guild.id]).values():
            tag.remove_from_cache()
            tag.command.remove_from_cache()
            del tag
        self.guild_tag_cache[guild.id].clear()
        await self.config.guild(guild).tags.clear()
        await ctx.send("Tags deleted.")

    @commands.is_owner()
    @slashtag.command(name="appid")
    async def slashtag_appid(self, ctx: commands.Context, id: int = None):
        """
        Manually set the application ID for [botname] slash commands if it differs from the bot user ID.

        This only applies to legacy bots. If you don't know what this means, you don't need to worry about it.
        """
        app_id = id or self.bot.user.id
        await self.config.application_id.set(app_id)
        self.application_id = app_id
        await ctx.send(f"Application ID set to `{id}`.")

    @commands.check(dev_check)
    @commands.is_owner()
    @slashtag.command(name="addeval")
    async def slashtag_addeval(self, ctx: commands.Context):
        """Add a slash eval command for debugging."""
        if self.eval_command:
            return await ctx.send("An eval command is already registered.")
        slasheval = SlashCommand(
            self,
            name="eval",
            description="SlashTags debugging eval command. Only bot owners can use this.",
            options=[
                SlashOption(name="body", description="Code body to evaluate.", required=True)
            ],
        )
        await slasheval.register()
        await self.config.eval_command.set(slasheval.id)
        self.eval_command = slasheval.id
        await ctx.send("`/eval` has been registered.")

    @commands.check(dev_check)
    @commands.is_owner()
    @slashtag.command(name="rmeval")
    async def slashtag_rmeval(self, ctx: commands.Context):
        """Remove the slash eval commands."""
        if not self.eval_command:
            return await ctx.send("The eval command hasn't been registered.")
        await self.http.remove_slash_command(self.eval_command)
        await self.config.eval_command.clear()
        self.eval_command = None
        await ctx.send("`/eval` has been deleted.")
