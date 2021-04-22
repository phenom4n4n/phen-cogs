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

import asyncio
import logging
from collections import defaultdict
from copy import copy
from functools import partial
from typing import Coroutine, Dict, List, Optional

import discord
import TagScriptEngine as tse
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import (box, humanize_list, inline,
                                               pagify)
from redbot.core.utils.menus import (DEFAULT_CONTROLS, menu,
                                     start_adding_reactions)
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate

from .blocks import HideBlock
from .context import SlashContext
from .converters import SLASH_NAME, TagConverter, TagName, TagScriptConverter
from .errors import (BlacklistCheckFailure, MissingTagPermissions,
                     RequireCheckFailure, WhitelistCheckFailure)
from .http import SlashHTTP
from .models import InteractionResponse, SlashOptionType
from .objects import CommandModel, FakeMessage, SlashOption, SlashTag

log = logging.getLogger("red.phenom4n4n.slashtags")

option = SlashOption(name="args", description="Arguments for the tag.", required=True)
optional_member = SlashOption(
    name="member", description="Server member", option_type=SlashOptionType.USER, required=False
)
empty_adapter = tse.StringAdapter("")

PL = commands.PrivilegeLevel
RS = commands.Requires


def dev_check(ctx: commands.Context):
    return ctx.bot.get_cog("Dev")


class SlashTags(commands.Cog):
    """
    Create custom slash commands.

    The TagScript documentation can be found [here](https://phen-cogs.readthedocs.io/en/latest/index.html).
    """

    __version__ = "0.2.0"
    __author__ = ["PhenoM4n4n"]

    OPTION_ADAPTERS = {
        SlashOptionType.STRING: tse.StringAdapter,
        SlashOptionType.INTEGER: tse.IntAdapter,
        SlashOptionType.BOOLEAN: tse.StringAdapter,
        SlashOptionType.USER: tse.MemberAdapter,
        SlashOptionType.CHANNEL: tse.ChannelAdapter,
        SlashOptionType.ROLE: tse.SafeObjectAdapter,
    }

    def format_help_for_context(self, ctx: commands.Context):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        text = [
            f"{pre_processed}{n}",
            f"Cog Version: **{self.__version__}**",
            f"TagScriptEngine Version: **{tse.__version__}**",
            f"Author: {humanize_list(self.__author__)}",
        ]
        return "\n".join(text)

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.application_id = None
        self.eval_command = None
        self.http = SlashHTTP(self)
        self.config = Config.get_conf(
            self,
            identifier=70342502093747959723475890,
            force_registration=True,
        )
        default_guild = {"tags": {}}
        default_global = {"application_id": None, "eval_command": None}
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)

        tse_blocks = [
            tse.MathBlock(),
            tse.RandomBlock(),
            tse.RangeBlock(),
            tse.AnyBlock(),
            tse.IfBlock(),
            tse.AllBlock(),
            tse.BreakBlock(),
            tse.StrfBlock(),
            tse.StopBlock(),
            tse.AssignmentBlock(),
            tse.FiftyFiftyBlock(),
            tse.LooseVariableGetterBlock(),
            tse.SubstringBlock(),
            tse.EmbedBlock(),
            tse.ReplaceBlock(),
            tse.PythonBlock(),
            tse.RequireBlock(),
            tse.BlacklistBlock(),
            tse.URLEncodeBlock(),
            tse.CommandBlock(),
        ]
        slash_blocks = [HideBlock()]
        self.engine = tse.Interpreter(tse_blocks + slash_blocks)
        self.role_converter = commands.RoleConverter()
        self.channel_converter = commands.TextChannelConverter()
        self.member_converter = commands.MemberConverter()
        self.emoji_converter = commands.EmojiConverter()

        self.command_cache = {}
        self.guild_tag_cache: Dict[int, Dict[int, SlashTag]] = defaultdict(dict)
        self.global_tag_cache = {}

        self.load_task = self.create_task(self.initialize_task())

        bot.add_dev_env_value("st", lambda ctx: self)

    async def red_delete_data_for_user(self, *, requester: str, user_id: int) -> None:
        return

    def task_done_callback(self, task: asyncio.Task):
        try:
            task.result()
        except Exception as error:
            log.exception(f"Task failed.", exc_info=error)

    def create_task(self, coroutine: Coroutine):
        task = asyncio.create_task(coroutine)
        task.add_done_callback(self.task_done_callback)
        return task

    def cog_unload(self):
        self.bot.remove_dev_env_value("st")
        self.load_task.cancel()

    async def cog_before_invoke(self, ctx: commands.Context) -> bool:
        if not self.bot.get_cog("SlashInjector"):
            raise commands.UserFeedbackCheckFailure(
                "This cog requires `slashinjector` by Kowlin/Sentinal to be loaded to parse slash command responses (<https://github.com/Kowlin/Sentinel>)."
            )
        return True

    async def pre_load(self):
        data = await self.config.all()
        self.eval_command = data["eval_command"]
        if app_id := data["application_id"]:
            self.application_id = app_id
        else:
            if self.bot.user is not None:
                app_id = self.bot.user.id
                await self.config.application_id.set(app_id)
                self.application_id = app_id

    async def initialize_task(self):
        await self.cache_tags()
        if self.application_id is None:
            await self.set_app_id()

    async def set_app_id(self):
        if self.bot.user is None:
            await self.bot.wait_until_ready()
        app_id = self.bot.user.id
        await self.config.application_id.set(app_id)
        self.application_id = app_id

    async def cache_tags(self):
        cached = 0
        guilds_data = await self.config.all_guilds()
        async for guild_id, guild_data in AsyncIter(guilds_data.items(), steps=100):
            async for tag_name, tag_data in AsyncIter(guild_data["tags"].items(), steps=50):
                tag = SlashTag.from_dict(self, tag_data, guild_id=guild_id)
                self.guild_tag_cache[guild_id][tag.id] = tag
                self.command_cache[tag.command.id] = tag.command
                cached += 1
        log.debug(f"slash tags cached: {cached}")

    async def validate_tagscript(self, ctx: commands.Context, tagscript: str):
        output = self.engine.process(tagscript)
        is_owner = await self.bot.is_owner(ctx.author)
        if is_owner:
            return True
        # TODO block validation
        return True

    def get_tag(self, guild: discord.Guild, tag_id: int) -> SlashTag:
        return self.guild_tag_cache[guild.id].get(tag_id)

    def get_tag_by_name(self, guild: discord.Guild, tag_name: str) -> SlashTag:
        for tag in self.guild_tag_cache[guild.id].values():
            if tag.name == tag_name:
                return tag

    def get_command(self, command_id: int) -> CommandModel:
        return self.command_cache.get(command_id)

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

        command = CommandModel(
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
        self.guild_tag_cache[ctx.guild.id][command.id] = tag
        self.command_cache[tag.command.id] = tag.command
        await tag.update_config()
        await ctx.send(f"Slash tag `{tag}` added with {len(command.options)} options.")

    async def get_options(
        self, ctx: commands.Context, options: List[SlashOption]
    ) -> List[SlashOption]:
        for i in range(1, 11):
            try:
                option = await self.get_option(ctx)
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
        timeout: int = 30,
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

    async def get_option(self, ctx: commands.Context) -> SlashOption:
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

        pred = MessagePredicate.yes_or_no(ctx)
        await self.send_and_query_response(ctx, "Is this argument required? (Y/n)", pred)
        required = pred.result

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
        old_tagscript = tag.tagscript
        tag.tagscript = tagscript
        await tag.update_config()
        await ctx.send(
            f"Slash tag `{tag}`'s tagscript has been edited from {len(old_tagscript)} to {len(tagscript)} characters."
        )

    @slashtag_edit.command(name="name")
    async def slashtag_edit_name(self, ctx: commands.Context, tag: TagConverter, name: TagName):
        """Edit a slash tag's name."""
        old_name = tag.name
        await tag.command.edit(name=name)
        await tag.update_config()
        await ctx.send(f"Renamed `{old_name}` to `{name}`.")

    @slashtag_edit.command(name="description")
    async def slashtag_edit_description(
        self, ctx: commands.Context, tag: TagConverter, *, description: str
    ):
        """Edit a slash tag's description."""
        await tag.command.edit(description=description)
        await tag.update_config()
        await ctx.send(f"Edited `{tag}`'s description.")

    @slashtag_edit.command(name="arguments")
    async def slashtag_edit_arguments(self, ctx: commands.Context, tag: TagConverter):
        """Edit a slash tag's arguments."""
        old_options = tag.command.options
        options = await self.get_options(ctx, [])
        await tag.command.edit(options=options)
        await tag.update_config()
        await ctx.send(
            f"Slash tag `{tag}`'s arguments have been edited from {len(old_options)} to {len(options)} arguments."
        )

    @commands.mod_or_permissions(manage_guild=True)
    @slashtag.command(name="remove", aliases=["delete", "-"])
    async def slashtag_remove(self, ctx: commands.Context, tag: TagConverter):
        """Delete a slash tag."""
        await tag.delete()
        await ctx.send(f"Slash tag `{tag}` deleted.")
        del tag

    @slashtag.command(name="info")
    async def slashtag_info(self, ctx: commands.Context, tag: TagConverter):
        """Get info about a slash tag that is stored on this server."""
        desc = [
            f"Author: {tag.author.mention if tag.author else tag.author_id}",
            f"Uses: {tag.uses}",
            f"Length: {len(tag)}",
        ]
        e = discord.Embed(
            color=await ctx.embed_color(),
            title=f"SlashTag `{tag}` Info",
            description="\n".join(desc),
        )
        c = tag.command
        command_info = [
            f"ID: `{c.id}`",
            f"Name: {c.name}",
            f"Description: {c.description}",
        ]
        e.add_field(name="Command", value="\n".join(command_info), inline=False)

        option_info = []
        for o in c.options:
            option_desc = [
                f"**{o.name}**",
                f"Description: {o.description}",
                f"Type: {o.type.name.title()}",
                f"Required: {o.required}",
            ]
            option_info.append("\n".join(option_desc))
        if option_info:
            e.add_field(name="Options", value="\n".join(option_info), inline=False)

        e.set_author(name=ctx.guild, icon_url=ctx.guild.icon_url)
        await ctx.send(embed=e)

    @slashtag.command(name="raw")
    async def slashtag_raw(self, ctx: commands.Context, tag: TagConverter):
        """Get a slash tag's raw content."""
        tagscript = discord.utils.escape_markdown(tag.tagscript)
        for page in pagify(tagscript):
            await ctx.send(
                page,
                allowed_mentions=discord.AllowedMentions.none(),
            )

    @slashtag.command(name="list")
    async def slashtag_list(self, ctx: commands.Context):
        """View stored slash tags."""
        tags = self.guild_tag_cache[ctx.guild.id]
        if not tags:
            return await ctx.send("There are no slash tags on this server.")
        description = []

        for tag_id, tag in tags.items():
            tagscript = tag.tagscript
            if len(tagscript) > 23:
                tagscript = tagscript[:20] + "..."
            tagscript = tagscript.replace("\n", " ")
            description.append(f"`{tag.name}` - {discord.utils.escape_markdown(tagscript)}")
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
        for tag_name, tag in copy(self.guild_tag_cache[guild.id]).items():
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
        slasheval = CommandModel(
            self,
            name="eval",
            description="SlashTags debugging eval command.",
            options=[option, optional_member],
        )
        await slasheval.register()
        await self.config.eval_command.set(slasheval.id)
        self.eval_command = slasheval.id
        await ctx.send("`/eval` has been registered.")

    @commands.check(dev_check)
    @commands.is_owner()
    @slashtag.command(name="rmeval")
    async def slashtag_rmeval(self, ctx: commands.Context):
        """Remove the slash eval."""
        if not self.eval_command:
            return await ctx.send("The eval command hasn't been registered.")
        await self.http.remove_slash_command(self.eval_command)
        await self.config.eval_command.clear()
        self.eval_command = None
        await ctx.send("`/eval` has been deleted.")

    @commands.Cog.listener(name="on_interaction_create")
    async def slash_command_parser(self, data: dict):
        log.debug("Interaction data received:\n%s" % data)
        try:
            interaction = InteractionResponse(data=data, cog=self)
        except Exception as e:
            log.exception(
                "An exception occured while parsing an interaction:\n%s" % data, exc_info=e
            )
            return
        try:
            await self.handle_interaction(interaction)
        except Exception as e:
            log.exception(
                "An exception occured while handling an interaction:\n%s" % data, exc_info=e
            )
            ctx = SlashContext.from_interaction(interaction)
            self.bot.dispatch("command_error", ctx, commands.CommandInvokeError(e))

    async def handle_interaction(self, interaction: InteractionResponse):
        # await interaction.defer()
        command = interaction.command
        if isinstance(command, CommandModel):
            tag = self.get_tag(interaction.guild, command.id)
            await self.process_tag(interaction, tag)
        elif interaction.command_id == self.eval_command:
            await self.slash_eval(interaction)

    async def slash_eval(self, interaction: InteractionResponse):
        await interaction.defer()
        if not await self.bot.is_owner(interaction.author):
            return await interaction.send("Only bot owners may eval.", hidden=True)
        ctx = SlashContext.from_interaction(interaction)
        dev = dev_check(self)
        await dev._eval(ctx, body=interaction.options[0].value)

    @staticmethod
    async def delete_quietly(message: discord.Message):
        try:
            await message.delete()
        except discord.HTTPException:
            pass

    def get_adapter(
        self, option_type: SlashOptionType, default: tse.Adapter = tse.StringAdapter
    ) -> tse.Adapter:
        return self.OPTION_ADAPTERS.get(option_type, default)

    async def process_tag(
        self,
        interaction: InteractionResponse,
        tag: SlashTag,
        *,
        seed_variables: dict = {},
        **kwargs,
    ) -> str:
        for option in interaction.options:
            seed_variables[option.name] = self.get_adapter(option.type)(option.value)
        for original_option in interaction.command.options:
            if original_option.name not in seed_variables:
                seed_variables[original_option.name] = empty_adapter

        guild = interaction.guild
        author = interaction.author
        channel = interaction.channel

        tag_author = tse.MemberAdapter(author)
        tag_channel = tse.ChannelAdapter(channel)
        seed = {
            "author": tag_author,
            "channel": tag_channel,
        }
        if guild:
            tag_guild = tse.GuildAdapter(guild)
            seed["server"] = tag_guild
        seed_variables.update(seed)

        output = tag.run(self.engine, seed_variables=seed_variables, **kwargs)
        await tag.update_config()
        to_gather = []
        content = output.body[:2000] if output.body else None
        actions = output.actions
        embed = actions.get("embed")
        command_messages = []
        hide = actions.get("hide", False)
        destination = interaction
        ctx = interaction
        # SlashContext.from_interaction ?

        if actions:
            try:
                await self.validate_checks(ctx, actions)
            except RequireCheckFailure as error:
                response = error.response
                if response is not None and response.strip():
                    await ctx.send(response[:2000], hidden=True)  # used hide?
                return

        if commands := actions.get("commands"):
            prefix = (await self.bot.get_valid_prefixes(interaction.guild))[0]
            for command in commands:
                message = FakeMessage.from_interaction(interaction, prefix + command)
                command_messages.append(message)

        # this is going to become an asynchronous swamp
        msg = None
        if content or embed is not None:
            msg = await self.send_tag_response(destination, content, embed=embed, hidden=hide)
        else:
            await interaction.defer()

        if command_messages:
            silent = actions.get("silent", False)
            overrides = actions.get("overrides")
            to_gather.append(
                self.process_commands(interaction, command_messages, silent, overrides)
            )

        if to_gather:
            await asyncio.gather(*to_gather)

    async def process_commands(
        self,
        interaction: InteractionResponse,
        messages: List[discord.Message],
        silent: bool,
        overrides: dict,
    ):
        command_tasks = []
        for message in messages:
            command_task = self.create_task(
                self.process_command(interaction, message, silent, overrides)
            )
            command_tasks.append(command_task)
            await asyncio.sleep(0.1)
        await asyncio.gather(*command_tasks)

    async def process_command(
        self,
        interaction: InteractionResponse,
        command_message: discord.Message,
        silent: bool,
        overrides: dict,
    ):
        ctx = await self.bot.get_context(
            command_message, cls=partial(SlashContext, interaction=interaction)
        )
        if ctx.valid:
            if overrides:
                command = copy(ctx.command)
                # command = commands.Command()
                # command = ctx.command.copy() # does not work as it makes ctx a regular argument
                requires: RS = copy(command.requires)
                priv_level = requires.privilege_level
                if priv_level not in (
                    PL.NONE,
                    PL.BOT_OWNER,
                    PL.GUILD_OWNER,
                ):
                    if overrides["admin"] and priv_level is PL.ADMIN:
                        requires.privilege_level = PL.NONE
                    elif overrides["mod"] and priv_level is PL.MOD:
                        requires.privilege_level = PL.NONE
                if overrides["permissions"] and requires.user_perms:
                    requires.user_perms = discord.Permissions.none()
                command.requires = requires
                ctx.command = command
            await self.bot.invoke(ctx)

    async def send_tag_response(
        self,
        destination: discord.abc.Messageable,
        content: str = None,
        **kwargs,
    ) -> Optional[discord.Message]:
        try:
            return await destination.send(content, **kwargs)
        except discord.HTTPException:
            pass

    async def validate_checks(self, ctx: commands.Context, actions: dict):
        to_gather = []
        if requires := actions.get("requires"):
            to_gather.append(self.validate_requires(ctx, requires))
        if blacklist := actions.get("blacklist"):
            to_gather.append(self.validate_blacklist(ctx, blacklist))
        if to_gather:
            await asyncio.gather(*to_gather)

    async def validate_requires(self, ctx: commands.Context, requires: dict):
        # sourcery skip: merge-duplicate-blocks
        for argument in requires["items"]:
            role_or_channel = await self.role_or_channel_convert(ctx, argument)
            if not role_or_channel:
                continue
            if isinstance(role_or_channel, discord.Role):
                if role_or_channel in ctx.author.roles:
                    return
            else:
                if role_or_channel == ctx.channel:
                    return
        raise RequireCheckFailure(requires["response"])

    async def validate_blacklist(self, ctx: commands.Context, blacklist: dict):
        # sourcery skip: merge-duplicate-blocks
        for argument in blacklist["items"]:
            role_or_channel = await self.role_or_channel_convert(ctx, argument)
            if not role_or_channel:
                continue
            if isinstance(role_or_channel, discord.Role):
                if role_or_channel in ctx.author.roles:
                    raise RequireCheckFailure(blacklist["response"])
            else:
                if role_or_channel == ctx.channel:
                    raise RequireCheckFailure(blacklist["response"])

    async def role_or_channel_convert(self, ctx: commands.Context, argument: str):
        objects = await asyncio.gather(
            self.role_converter.convert(ctx, argument),
            self.channel_converter.convert(ctx, argument),
            return_exceptions=True,
        )
        objects = [obj for obj in objects if isinstance(obj, (discord.Role, discord.TextChannel))]
        return objects[0] if objects else None
