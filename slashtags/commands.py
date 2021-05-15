import asyncio
import re
import types
from copy import copy
from typing import Dict, List, Union

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_list, inline, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils.predicates import MessagePredicate

from .abc import MixinMeta
from .converters import (
    GlobalTagConverter,
    GuildTagConverter,
    TagConverter,
    TagName,
    TagScriptConverter,
)
from .errors import (
    BlacklistCheckFailure,
    MissingTagPermissions,
    RequireCheckFailure,
    WhitelistCheckFailure,
)
from .http import SlashHTTP
from .models import SlashOptionType
from .objects import (
    FakeMessage,
    SlashCommand,
    SlashContext,
    SlashOption,
    SlashOptionChoice,
    SlashTag,
)
from .utils import ARGUMENT_NAME_DESCRIPTION, dev_check

TAG_RE = re.compile(r"(?i)(\[p\])?\b(slash\s?)?tag'?s?\b")

CHOICE_RE = re.compile(r".{1,100}:.{1,100}")

CHOICE_LIMIT = 25


def _sub(match: re.Match) -> str:
    if match.group(1):
        return "[p]slashtag global"

    repl = "global "
    name = match.group(0)
    repl += name
    if name.istitle():
        repl = repl.title()
    return repl


def copy_doc(original: Union[commands.Command, types.FunctionType]):
    def decorator(overriden: Union[commands.Command, types.FunctionType]):
        doc = original.help if isinstance(original, commands.Command) else original.__doc__
        doc = TAG_RE.sub(_sub, doc)

        if isinstance(overriden, commands.Command):
            overriden._help_override = doc
        else:
            overriden.__doc__ = doc
        return overriden

    return decorator


class Commands(MixinMeta):
    @commands.guild_only()
    @commands.group(aliases=["st"])
    async def slashtag(self, ctx: commands.Context):
        """
        Slash Tag management with TagScript.

        These commands use TagScriptEngine.
        [This site](https://phen-cogs.readthedocs.io/en/latest/index.html) has documentation on how to use TagScript blocks.
        """

    @commands.mod_or_permissions(manage_guild=True)
    @slashtag.command("add", aliases=["create", "+"])
    async def slashtag_add(
        self,
        ctx: commands.Context,
        tag_name: TagName(check_global=False),
        *,
        tagscript: TagScriptConverter,
    ):
        """
        Add a slash tag with TagScript.

        [Slash tag usage guide](https://phen-cogs.readthedocs.io/en/latest/slashtags.html)
        """
        await self.create_slash_tag(ctx, tag_name, tagscript, is_global=False)

    async def create_slash_tag(
        self, ctx: commands.Context, tag_name: str, tagscript: str, *, is_global: bool = False
    ):
        options: List[SlashOption] = []
        guild_id = None if is_global else ctx.guild.id
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
            self, name=tag_name, description=description, guild_id=guild_id, options=options
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
            guild_id=guild_id,
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

    async def get_choices(self, ctx: commands.Context) -> List[SlashOptionChoice]:
        query = (
            "Send the list of choice names and values you would like to add as choices to "
            "the tag. Choice names and values should be seperated by `:`, and each choice "
            "should be seperated by `|`. Example:\n`dog:Doggo|cat:Catto`"
        )
        response = await self.send_and_query_response(ctx, query)
        choices = []
        for index, choice_text in enumerate(response.split("|"), 1):
            if ":" not in choice_text:
                await ctx.send(
                    f"Failed to parse `{choice_text}` to a choice as its name and value "
                    "weren't seperated by a `:`.",
                    delete_after=15,
                )
                continue
            if not CHOICE_RE.match(choice_text):
                await ctx.send(
                    f"Failed to parse `{choice_text}` to a choice as "
                    "its name or value exceeded the 100 character limit.",
                    delete_after=15,
                )
                continue
            choice = SlashOptionChoice(*choice_text.split(":", 1))
            choices.append(choice)
            if len(choices) >= CHOICE_LIMIT:
                await ctx.send(f"Reached max choices ({CHOICE_LIMIT}).")
                break
        return choices

    async def get_option(
        self, ctx: commands.Context, *, added_required: bool = False
    ) -> SlashOption:
        name_desc = [
            "What should the argument name be and description be?",
            "The argument name and description should be split by a `:`.",
            "Example: `member:A member of this server.`\n",
            "*Slash argument names may not exceed 32 characters and can only contain characters "
            "that are alphanumeric or '_' or '-'.",
            "The argument description must be less than or equal to 100 characters.*",
        ]
        name_pred = MessagePredicate.regex(ARGUMENT_NAME_DESCRIPTION, ctx)
        await self.send_and_query_response(ctx, "\n".join(name_desc), name_pred)
        match = name_pred.result
        name, description = match.group(1), match.group(2)

        valid_option_types = [
            name.lower()
            for name in SlashOptionType.__members__.keys()
            if not name.startswith("SUB")
        ]
        valid_option_types.append("choices")

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
        if option_type == "choices":
            choices = await self.get_choices(ctx)
            option_type = "STRING"
        else:
            choices = []
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
            name=name,
            description=description,
            option_type=option_type,
            required=required,
            choices=choices,
        )

    @commands.mod_or_permissions(manage_guild=True)
    @slashtag.group("edit", aliases=["e"], invoke_without_command=True)
    async def slashtag_edit(
        self, ctx: commands.Context, tag: GuildTagConverter, *, tagscript: TagScriptConverter
    ):
        """Edit a slash tag."""
        await ctx.send(await tag.edit_tagscript(tagscript))

    @slashtag_edit.command("tagscript")
    async def slashtag_edit_tagscript(
        self, ctx: commands.Context, tag: GuildTagConverter, *, tagscript: TagScriptConverter
    ):
        """Edit a slash tag's TagScript."""
        await self.slashtag_edit(ctx, tag, tagscript=tagscript)

    @slashtag_edit.command("name")
    async def slashtag_edit_name(
        self, ctx: commands.Context, tag: GuildTagConverter, name: TagName(check_global=False)
    ):
        """Edit a slash tag's name."""
        await ctx.send(tag.edit_name(name))

    @slashtag_edit.command("description")
    async def slashtag_edit_description(
        self, ctx: commands.Context, tag: GuildTagConverter, *, description: str
    ):
        """Edit a slash tag's description."""
        await ctx.send(await tag.edit_description(description))

    @slashtag_edit.command("arguments", aliases=["options"])
    async def slashtag_edit_arguments(self, ctx: commands.Context, tag: GuildTagConverter):
        """
        Edit a slash tag's arguments.

        See [this documentation page](https://phen-cogs.readthedocs.io/en/latest/slash_arguments.html) for more information on slash tag arguments.
        """
        await tag.edit_options(ctx)

    @slashtag_edit.command("argument", aliases=["option"])
    async def slashtag_edit_argument(
        self, ctx: commands.Context, tag: GuildTagConverter, argument: str
    ):
        """Edit a single slash tag's argument by name."""
        await tag.edit_single_option(ctx, argument)

    @commands.mod_or_permissions(manage_guild=True)
    @slashtag.command("remove", aliases=["delete", "-"])
    async def slashtag_remove(self, ctx: commands.Context, tag: GuildTagConverter):
        """Delete a slash tag."""
        await ctx.send(await tag.delete())

    @slashtag.command("info")
    async def slashtag_info(self, ctx: commands.Context, tag: TagConverter):
        """Get info about a slash tag that is stored on this server."""
        await tag.send_info(ctx)

    @slashtag.command("raw")
    async def slashtag_raw(self, ctx: commands.Context, tag: GuildTagConverter):
        """Get a slash tag's raw content."""
        await tag.send_raw_tagscript(ctx)

    @staticmethod
    def format_tagscript(tag: SlashTag, limit: int = 60) -> str:
        prefix = f"`/{tag.name}` - "
        limit -= len(prefix)
        tagscript = tag.tagscript
        if len(tagscript) > limit - 3:
            tagscript = tagscript[:limit] + "..."
        tagscript = tagscript.replace("\n", " ")
        return f"{prefix}{discord.utils.escape_markdown(tagscript)}"

    async def view_slash_tags(
        self,
        ctx: commands.Context,
        tags: Dict[int, SlashTag],
        *,
        is_global: bool,
    ):
        description = [self.format_tagscript(tag) for tag in tags.values()]
        description = "\n".join(description)

        e = discord.Embed(color=await ctx.embed_color())
        if is_global:
            slash_tags = "global slash tags"
            e.set_author(name="Global Slash Tags", icon_url=ctx.me.avatar_url)
        else:
            slash_tags = "slash tags"
            e.set_author(name="Stored Slash Tags", icon_url=ctx.guild.icon_url)

        embeds = []
        pages = list(pagify(description))
        for index, page in enumerate(pages, 1):
            embed = e.copy()
            embed.description = page
            embed.set_footer(text=f"{index}/{len(pages)} | {len(tags)} {slash_tags}")
            embeds.append(embed)
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @slashtag.command("list")
    async def slashtag_list(self, ctx: commands.Context):
        """View stored slash tags."""
        tags = self.guild_tag_cache[ctx.guild.id]
        if not tags:
            return await ctx.send("There are no slash tags on this server.")
        await self.view_slash_tags(ctx, tags, is_global=False)

    @commands.is_owner()
    @slashtag.command("clear", hidden=True)
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
    @slashtag.group("global")
    @copy_doc(slashtag)
    async def slashtag_global(self, ctx: commands.Context):
        pass

    @slashtag_global.command("add")
    @copy_doc(slashtag_add)
    async def slashtag_global_add(
        self,
        ctx: commands.Context,
        tag_name: TagName(global_priority=True),
        *,
        tagscript: TagScriptConverter,
    ):
        await self.create_slash_tag(ctx, tag_name, tagscript, is_global=True)

    @slashtag_global.group("edit", aliases=["e"], invoke_without_command=True)
    @copy_doc(slashtag_edit)
    async def slashtag_global_edit(
        self, ctx: commands.Context, tag: GlobalTagConverter, *, tagscript: TagScriptConverter
    ):
        await ctx.send(await tag.edit_tagscript(tagscript))

    @slashtag_global_edit.command("tagscript")
    @copy_doc(slashtag_edit_tagscript)
    async def slashtag_global_edit_tagscript(
        self, ctx: commands.Context, tag: GlobalTagConverter, *, tagscript: TagScriptConverter
    ):
        await self.slashtag_global_edit(ctx, tag, tagscript=tagscript)

    @slashtag_global_edit.command("name")
    @copy_doc(slashtag_edit_name)
    async def slashtag_global_edit_name(
        self, ctx: commands.Context, tag: GlobalTagConverter, name: TagName(global_priority=True)
    ):
        await ctx.send(tag.edit_name(name))

    @slashtag_global_edit.command("description")
    @copy_doc(slashtag_edit_description)
    async def slashtag_global_edit_description(
        self, ctx: commands.Context, tag: GlobalTagConverter, *, description: str
    ):
        await ctx.send(await tag.edit_description(description))

    @slashtag_global_edit.command("arguments", aliases=["options"])
    @copy_doc(slashtag_edit_arguments)
    async def slashtag_global_edit_arguments(self, ctx: commands.Context, tag: GlobalTagConverter):
        await tag.edit_options(ctx)

    @slashtag_global_edit.command("argument", aliases=["option"])
    @copy_doc(slashtag_edit_argument)
    async def slashtag_global_edit_argument(
        self, ctx: commands.Context, tag: GuildTagConverter, argument: str
    ):
        """Edit a single slash tag's argument by name."""
        await tag.edit_single_option(ctx, argument)

    @slashtag_global.command("remove", aliases=["delete", "-"])
    @copy_doc(slashtag_remove)
    async def slashtag_global_remove(self, ctx: commands.Context, tag: GlobalTagConverter):
        await ctx.send(await tag.delete())

    @slashtag_global.command("raw")
    @copy_doc(slashtag_raw)
    async def slashtag_global_raw(self, ctx: commands.Context, tag: GlobalTagConverter):
        await tag.send_raw_tagscript(ctx)

    @slashtag_global.command("list")
    @copy_doc(slashtag_list)
    async def slashtag_global_list(self, ctx: commands.Context):
        tags = self.global_tag_cache
        if not tags:
            return await ctx.send("There are no global slash tags.")
        await self.view_slash_tags(ctx, tags, is_global=True)

    @commands.is_owner()
    @commands.group(aliases=["slashset"])
    async def slashtagset(self, ctx: commands.Context):
        """Manage SlashTags settings."""

    @slashtagset.command("settings")
    async def slashtagset_settings(self, ctx: commands.Context):
        """View SlashTags settings."""
        eval_command = f"✅ (**{self.eval_command}**)" if self.eval_command else "❎"
        description = [
            f"Application ID: **{self.application_id}**",
            f"Eval command: {eval_command}",
        ]
        embed = discord.Embed(
            color=0xC9C9C9, title="SlashTags Settings", description="\n".join(description)
        )
        await ctx.send(embed=embed)

    @slashtagset.command("appid")
    async def slashtagset_appid(self, ctx: commands.Context, id: int = None):
        """
        Manually set the application ID for [botname] slash commands if it differs from the bot user ID.

        This only applies to legacy bots. If you don't know what this means, you don't need to worry about it.
        """
        app_id = id or self.bot.user.id
        await self.config.application_id.set(app_id)
        self.application_id = app_id
        await ctx.send(f"Application ID set to `{id}`.")

    @commands.check(dev_check)
    @slashtagset.command("addeval")
    async def slashtagset_addeval(self, ctx: commands.Context):
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
    @slashtagset.command("rmeval")
    async def slashtagset_rmeval(self, ctx: commands.Context):
        """Remove the slash eval command."""
        if not self.eval_command:
            return await ctx.send("The eval command hasn't been registered.")
        await self.http.remove_slash_command(self.eval_command)
        await self.config.eval_command.clear()
        self.eval_command = None
        await ctx.send("`/eval` has been deleted.")
