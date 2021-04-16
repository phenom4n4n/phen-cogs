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
import time
from collections import defaultdict
from copy import copy
from typing import Optional, List
from urllib.parse import quote_plus

import logging
import discord
from discord.utils import escape_markdown
from redbot.core import commands
from redbot.core.commands import Requires, PrivilegeLevel
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import box, humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, close_menu, menu, start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate, MessagePredicate
from redbot.cogs.alias.alias import Alias
import TagScriptEngine as tse
import aiohttp
import bs4

from .blocks import *
from .converters import TagConverter, TagName, TagScriptConverter
from .objects import Tag
from .ctx import SilentContext
from .errors import (
    MissingTagPermissions,
    RequireCheckFailure,
    WhitelistCheckFailure,
    BlacklistCheckFailure,
)


log = logging.getLogger("red.phenom4n4n.tags")


DOCS_URL = "https://phen-cogs.readthedocs.io/en/latest/"


async def send_quietly(destination: discord.abc.Messageable, content: str = None, **kwargs):
    try:
        return await destination.send(content, **kwargs)
    except discord.HTTPException:
        pass


class Tags(commands.Cog):
    """
    Create and use tags.

    The TagScript documentation can be found [here](https://phen-cogs.readthedocs.io/en/latest/).
    """

    __version__ = "2.1.6"

    def format_help_for_context(self, ctx: commands.Context):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        text = [
            f"{pre_processed}{n}",
            f"Cog Version: **{self.__version__}**",
            f"TagScriptEngine Version: **{tse.__version__}**",
        ]
        return "\n".join(text)

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=567234895692346562369,
            force_registration=True,
        )
        default_guild = {"tags": {}}
        default_global = {"tags": {}}
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
            tse.ShortCutRedirectBlock("args"),
            tse.LooseVariableGetterBlock(),
            tse.SubstringBlock(),
            tse.EmbedBlock(),
            tse.ReplaceBlock(),
            tse.PythonBlock(),
            tse.URLEncodeBlock(),
            tse.RequireBlock(),
            tse.BlacklistBlock(),
            tse.CommandBlock(),
            tse.OverrideBlock(),
        ]
        tag_blocks = [
            DeleteBlock(),
            SilentBlock(),
            ReactBlock(),
            RedirectBlock(),
            ReactUBlock(),
        ]
        self.engine = tse.Interpreter(tse_blocks + tag_blocks)
        self.role_converter = commands.RoleConverter()
        self.channel_converter = commands.TextChannelConverter()
        self.member_converter = commands.MemberConverter()
        self.emoji_converter = commands.EmojiConverter()

        self.guild_tag_cache = defaultdict(dict)
        self.global_tag_cache = {}
        self.task = asyncio.create_task(self.cache_tags())

        self.session = aiohttp.ClientSession()
        self.docs: list = []

        bot.add_dev_env_value("tags", lambda ctx: self)

    def cog_unload(self):
        self.bot.remove_dev_env_value("tags")
        if self.task:
            self.task.cancel()
        asyncio.create_task(self.session.close())

    async def red_delete_data_for_user(self, *, requester: str, user_id: int):
        if requester not in ("discord_deleted_user", "user"):
            return
        guilds_data = await self.config.all_guilds()
        for guild_id, data in guilds_data.items():
            guild = self.bot.get_guild(guild_id)
            if guild and data["tags"]:
                for name, tag in data["tags"].items():
                    if str(user_id) in str(tag["author"]):
                        async with self.config.guild(guild).tags() as t:
                            del t[name]

    async def cache_tags(self):
        guilds_data = await self.config.all_guilds()
        async for guild_id, guild_data in AsyncIter(guilds_data.items(), steps=100):
            async for tag_name, tag_data in AsyncIter(guild_data["tags"].items(), steps=50):
                tag = Tag.from_dict(self, tag_name, tag_data, guild_id=guild_id)
                self.guild_tag_cache[guild_id][tag_name] = tag
                for alias in tag.aliases:
                    self.guild_tag_cache[alias] = tag

        global_tags = await self.config.tags()
        async for global_tag_name, global_tag_data in AsyncIter(global_tags.items(), steps=50):
            global_tag = Tag.from_dict(self, global_tag_name, global_tag_data)
            self.global_tag_cache[global_tag_name] = global_tag
            for alias in global_tag.aliases:
                self.global_tag_cache[alias] = global_tag

        log.debug("tag cache built")

    def get_tag(
        self,
        guild: Optional[discord.Guild],
        tag_name: str,
        *,
        check_global: bool = True,
        global_priority: bool = False,
    ) -> Optional[Tag]:
        tag = None
        if global_priority and check_global:
            return self.global_tag_cache.get(tag_name)
        if guild is not None:
            tag = self.guild_tag_cache[guild.id].get(tag_name)
        if tag is None and check_global:
            tag = self.global_tag_cache.get(tag_name)
        return tag

    async def validate_tagscript(self, ctx: commands.Context, tagscript: str):
        output = self.engine.process(tagscript)
        is_owner = await self.bot.is_owner(ctx.author)
        if is_owner:
            return True
        author_perms = ctx.channel.permissions_for(ctx.author)
        if output.actions.get("overrides"):
            if not author_perms.manage_guild:
                raise MissingTagPermissions(
                    "You must have **Manage Server** permissions to use the `override` block."
                )
        if output.actions.get("allowed_mentions"):
            # if not author_perms.mention_everyone:
            if not is_owner:
                raise MissingTagPermissions(
                    "You must have **Mention Everyone** permissions to use the `allowedmentions` block."
                )
        return True

    @commands.command(usage="<tag_name> [args]")
    async def invoketag(
        self, ctx, response: Optional[bool], tag_name: str, *, args: Optional[str] = ""
    ):
        """
        Manually invoke a tag with its name and arguments.

        Restricting this command with permissions in servers will restrict all members from invoking tags.
        """
        response = response or True
        try:
            _tag = await TagConverter(check_global=True).convert(ctx, tag_name)
        except commands.BadArgument as e:
            if response is True:
                await ctx.send(e)
        else:
            seed = {"args": tse.StringAdapter(args)}
            await self.process_tag(ctx, _tag, seed_variables=seed)

    @commands.guild_only()
    @commands.group(aliases=["customcom"])
    async def tag(self, ctx: commands.Context):
        """
        Tag management with TagScript.

        These commands use TagScriptEngine. [This site](https://phen-cogs.readthedocs.io/en/latest/) has documentation on how to use TagScript blocks.
        """

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command(name="add", aliases=["create", "+"])
    async def tag_add(
        self, ctx: commands.Context, tag_name: TagName, *, tagscript: TagScriptConverter
    ):
        """
        Add a tag with TagScript.

        [Tag usage guide](https://phen-cogs.readthedocs.io/en/latest/blocks.html#usage)
        """
        tag = self.get_tag(ctx.guild, tag_name)
        if tag:
            msg = await ctx.send(
                f"`{tag_name}` is already registered tag. Would you like to overwrite it?"
            )
            start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
            pred = ReactionPredicate.yes_or_no(msg, ctx.author)
            try:
                await ctx.bot.wait_for("reaction_add", check=pred, timeout=30)
            except asyncio.TimeoutError:
                return await ctx.send("Tag edit cancelled.")

            if pred.result is False:
                return await ctx.send("Tag edit cancelled.")
            tag.tagscript = tagscript
            await tag.update_config()
            await ctx.send(f"Tag `{tag}` edited.")
            return

        tag = Tag(self, tag_name, tagscript, author_id=ctx.author.id, guild_id=ctx.guild.id)
        self.guild_tag_cache[ctx.guild.id][tag_name] = tag
        await tag.update_config()
        await ctx.send(f"Tag `{tag}` added.")

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command(name="edit", aliases=["e"])
    async def tag_edit(
        self, ctx: commands.Context, tag: TagConverter, *, tagscript: TagScriptConverter
    ):
        """Edit a tag with TagScript."""
        tag.tagscript = tagscript
        await tag.update_config()
        await ctx.send(f"Tag `{tag}` edited.")

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command(name="remove", aliases=["delete", "-"])
    async def tag_remove(self, ctx: commands.Context, tag: TagConverter):
        """Delete a tag."""
        await tag.delete()
        await ctx.send(f"Tag `{tag}` deleted.")

    @tag.command(name="info")
    async def tag_info(self, ctx: commands.Context, tag: TagConverter):
        """Get info about a tag that is stored on this server."""
        desc = [
            f"Author: {tag.author.mention if tag.author else tag.author_id}",
            f"Uses: {tag.uses}",
            f"Length: {len(tag)}",
        ]
        e = discord.Embed(
            color=await ctx.embed_color(),
            title=f"Tag `{tag}` Info",
            description="\n".join(desc),
        )
        e.set_author(name=ctx.guild, icon_url=ctx.guild.icon_url)
        await ctx.send(embed=e)

    @tag.command(name="raw")
    async def tag_raw(self, ctx: commands.Context, tag: TagConverter):
        """Get a tag's raw content."""
        tagscript = escape_markdown(tag.tagscript)
        for page in pagify(tagscript):
            await ctx.send(
                page,
                allowed_mentions=discord.AllowedMentions.none(),
            )

    @tag.command(name="list")
    async def tag_list(self, ctx: commands.Context):
        """View stored tags."""
        tags = self.guild_tag_cache[ctx.guild.id]
        if not tags:
            return await ctx.send("There are no stored tags on this server.")
        description = []

        for name, tag in tags.items():
            tagscript = tag.tagscript
            if len(tagscript) > 23:
                tagscript = tagscript[:20] + "..."
            tagscript = tagscript.replace("\n", " ")
            description.append(f"`{name}` - {escape_markdown(tagscript)}")
        description = "\n".join(description)

        e = discord.Embed(color=await ctx.embed_color())
        e.set_author(name="Stored Tags", icon_url=ctx.guild.icon_url)

        embeds = []
        pages = list(pagify(description))
        for index, page in enumerate(pages, 1):
            embed = e.copy()
            embed.description = page
            embed.set_footer(text=f"{index}/{len(pages)} | {len(tags)} tags")
            embeds.append(embed)
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @tag.command(name="docs")
    async def tag_docs(self, ctx: commands.Context, keyword: str = None):
        """
        Search the Tag documentation for a block.

        https://phen-cogs.readthedocs.io/en/latest/
        """
        await ctx.trigger_typing()
        e = discord.Embed(color=await ctx.embed_color(), title="Tags Documentation")
        if keyword:
            doc_tags = await self.doc_search(keyword)
            description = [f"Search for: `{keyword}`"]
            for doc_tag in doc_tags:
                href = doc_tag.get("href")
                description.append(f"[`{doc_tag.text}`]({DOCS_URL}{href})")
            url = f"{DOCS_URL}search.html?q={quote_plus(keyword)}&check_keywords=yes&area=default"
            e.url = url
            embeds = []
            description = "\n".join(description)
            for page in pagify(description):
                embed = e.copy()
                embed.description = page
                embeds.append(embed)
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e.url = DOCS_URL
            await ctx.send(embed=e)

    async def doc_fetch(self):
        # from https://github.com/eunwoo1104/slash-bot/blob/8162fd5a0b6ac6c372486438e498a3140b5970bb/modules/sphinx_parser.py#L5
        async with self.session.get(f"{DOCS_URL}genindex.html") as response:
            text = await response.read()
        soup = bs4.BeautifulSoup(text, "html.parser")
        self.docs = soup.findAll("a")

    async def doc_search(self, keyword: str) -> List[bs4.Tag]:
        keyword = keyword.lower()
        if not self.docs:
            await self.doc_fetch()
        return [x for x in self.docs if keyword in str(x).lower()]

    @commands.is_owner()
    @tag.command(name="run", aliases=["execute"])
    async def tag_run(self, ctx: commands.Context, *, tagscript: str):
        """Execute TagScript without storing."""
        start = time.monotonic()
        author = tse.MemberAdapter(ctx.author)
        target = tse.MemberAdapter(ctx.message.mentions[0]) if ctx.message.mentions else author
        channel = tse.ChannelAdapter(ctx.channel)
        guild = tse.GuildAdapter(ctx.guild)
        seed = {
            "author": author,
            "user": author,
            "target": target,
            "member": target,
            "channel": channel,
            "guild": guild,
            "server": guild,
        }
        output = self.engine.process(tagscript, seed_variables=seed)
        end = time.monotonic()

        e = discord.Embed(
            color=await ctx.embed_color(),
            title="TagScriptEngine",
            description=f"Executed in **{round((end - start) * 1000, 3)}** ms",
        )
        e.add_field(name="Input", value=tagscript, inline=False)
        if output.actions:
            e.add_field(name="Actions", value=output.actions, inline=False)
        if output.variables:
            vars = "\n".join(
                f"{name}: {type(obj).__name__}" for name, obj in output.variables.items()
            )

            e.add_field(name="Variables", value=vars, inline=False)
        e.add_field(name="Output", value=output.body or "NO OUTPUT", inline=False)

        await ctx.send(embed=e)

    @commands.is_owner()
    @tag.command(name="process")
    async def tag_process(self, ctx: commands.Context, *, tagscript: str):
        """Process TagScript without storing."""
        tag = Tag(
            self,
            "processed_tag",
            tagscript,
            author_id=ctx.author.id,
            real=False,
        )
        await self.process_tag(ctx, tag)
        await ctx.tick()

    @commands.is_owner()
    @tag.group(name="global")
    async def tag_global(self, ctx: commands.Context):
        """Manage global tags."""

    @tag_global.command(name="add", aliases=["create", "+"])
    async def tag_global_add(
        self, ctx: commands.Context, tag_name: TagName, *, tagscript: TagScriptConverter
    ):
        """
        Add a global tag with TagScript.

        [Tag usage guide](https://phen-cogs.readthedocs.io/en/latest/blocks.html#usage)
        """
        tag = self.get_tag(None, tag_name, check_global=True)
        if tag:
            msg = await ctx.send(
                f"`{tag_name}` is already registered global tag. Would you like to overwrite it?"
            )
            start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
            pred = ReactionPredicate.yes_or_no(msg, ctx.author)
            try:
                await ctx.bot.wait_for("reaction_add", check=pred, timeout=30)
            except asyncio.TimeoutError:
                return await ctx.send("Global tag edit cancelled.")

            if pred.result is False:
                return await ctx.send("Global tag edit cancelled.")
            tag.tagscript = tagscript
            await tag.update_config()
            await ctx.send(f"Global tag `{tag}` edited.")
            return

        tag = Tag(self, tag_name, tagscript, author_id=ctx.author.id)
        self.global_tag_cache[tag_name] = tag
        await tag.update_config()
        await ctx.send(f"Global tag `{tag}` added.")

    @tag_global.command(name="edit", aliases=["e"])
    async def tag_global_edit(
        self,
        ctx: commands.Context,
        tag: TagConverter(check_global=True, global_priority=True),
        *,
        tagscript: TagScriptConverter,
    ):
        """Edit a global tag with TagScript."""
        tag.tagscript = tagscript
        await tag.update_config()
        await ctx.send(f"Global tag `{tag}` edited.")

    @tag_global.command(name="remove", aliases=["delete", "-"])
    async def tag_global_remove(
        self, ctx: commands.Context, tag: TagConverter(check_global=True, global_priority=True)
    ):
        """Delete a global tag."""
        await tag.delete()
        await ctx.send(f"Global tag `{tag}` deleted.")

    @tag_global.command(name="info")
    async def tag_global_info(
        self, ctx: commands.Context, tag: TagConverter(check_global=True, global_priority=True)
    ):
        """Get info about a global tag."""
        desc = [
            f"Author: {tag.author.mention if tag.author else tag.author_id}",
            f"Uses: {tag.uses}",
            f"Length: {len(tag)}",
        ]
        e = discord.Embed(
            color=await ctx.embed_color(),
            title=f"Tag `{tag}` Info",
            description="\n".join(desc),
        )
        e.set_author(name=ctx.me, icon_url=ctx.me.avatar_url)
        await ctx.send(embed=e)

    @tag_global.command(name="raw")
    async def tag_global_raw(
        self, ctx: commands.Context, tag: TagConverter(check_global=True, global_priority=True)
    ):
        """Get a tag's raw content."""
        tagscript = escape_markdown(tag.tagscript)
        for page in pagify(tagscript):
            await ctx.send(
                page,
                allowed_mentions=discord.AllowedMentions.none(),
            )

    @tag_global.command(name="list")
    async def tag_global_list(self, ctx: commands.Context):
        """View stored tags."""
        tags = self.global_tag_cache
        if not tags:
            return await ctx.send("There are no global tags.")
        description = []

        for name, tag in tags.items():
            tagscript = tag.tagscript
            if len(tagscript) > 23:
                tagscript = tagscript[:20] + "..."
            tagscript = tagscript.replace("\n", " ")
            description.append(f"`{name}` - {escape_markdown(tagscript)}")
        description = "\n".join(description)

        e = discord.Embed(color=await ctx.embed_color())
        e.set_author(name="Global Tags", icon_url=ctx.me.avatar_url)

        embeds = []
        pages = list(pagify(description))
        for index, page in enumerate(pages, 1):
            embed = e.copy()
            embed.description = page
            embed.set_footer(text=f"{index}/{len(pages)} | {len(tags)} tags")
            embeds.append(embed)
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @commands.is_owner()
    @commands.command()
    async def migratealias(self, ctx: commands.Context):
        """Migrate alias global and guild configs to tags."""
        alias_cog = self.bot.get_cog("Alias")
        if not alias_cog:
            return await ctx.send("Alias cog must be loaded to migrate data.")

        query = await ctx.send(f"Are you sure you want to migrate alias data to tags? (Y/n)")
        pred = MessagePredicate.yes_or_no(ctx)
        try:
            response = await self.bot.wait_for("message", check=pred, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send("Query timed out, not migrating alias to tags.")

        if pred.result is False:
            return await ctx.send("Migration cancelled.")

        migrated_guilds = 0
        migrated_guild_alias = 0
        all_guild_data: dict = await alias_cog.config.all_guilds()

        async for guild_id, guild_data in AsyncIter(all_guild_data.items(), steps=100):
            if not guild_data["entries"]:
                continue
            migrated_guilds += 1
            for alias in guild_data["entries"]:
                tagscript = "{c:" + alias["command"] + " {args}}"
                tag = Tag(
                    self,
                    alias["name"],
                    tagscript,
                    author_id=alias["creator"],
                    guild_id=alias["guild"],
                    uses=alias["uses"],
                )
                self.guild_tag_cache[guild_id][alias["name"]] = tag
                await tag.update_config()
                migrated_guild_alias += 1
        await ctx.send(
            f"Migrated {migrated_guild_alias} aliases from {migrated_guilds} "
            "servers to tags. Moving on to global aliases.."
        )

        migrated_global_alias = 0
        async for entry in AsyncIter(await alias_cog.config.entries(), steps=50):
            tagscript = "{c:" + entry["command"] + " {args}}"
            global_tag = Tag(
                self,
                entry["name"],
                tagscript,
                author_id=entry["creator"],
                uses=entry["uses"],
            )
            self.global_tag_cache[entry["name"]] = global_tag
            await global_tag.update_config()
            migrated_global_alias += 1
        await ctx.send(
            f"Migrated {migrated_global_alias} global aliases to tags. "
            "Migration completed, unload the alias cog to prevent command "
            f"duplication with `{ctx.clean_prefix}unload alias`."
        )

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot:
            return

        try:
            prefix = await Alias.get_prefix(self, message)
        except ValueError:
            return
        tag_command = message.content[len(prefix) :]
        tag_split = tag_command.split(" ", 1)
        if self.get_tag(
            message.guild, tag_split[0], check_global=True
        ) and await self.message_eligible_as_tag(message):
            await self.invoke_tag_message(message, prefix, tag_command)

    async def message_eligible_as_tag(self, message: discord.Message) -> bool:
        if message.guild:
            return isinstance(
                message.author, discord.Member
            ) and await self.bot.message_eligible_as_command(message)
        else:
            return await self.bot.allowed_by_whitelist_blacklist(message.author)

    async def invoke_tag_message(self, message: discord.Message, prefix: str, tag_command: str):
        new_message = copy(message)
        new_message.content = f"{prefix}invoketag False {tag_command}"
        ctx = await self.bot.get_context(new_message)
        await self.bot.invoke(ctx)

    async def process_tag(
        self, ctx: commands.Context, tag: Tag, *, seed_variables: dict = {}, **kwargs
    ) -> str:
        author = tse.MemberAdapter(ctx.author)
        target = tse.MemberAdapter(ctx.message.mentions[0]) if ctx.message.mentions else author
        channel = tse.ChannelAdapter(ctx.channel)
        seed = {
            "author": author,
            "user": author,
            "target": target,
            "member": target,
            "channel": channel,
        }
        if ctx.guild:
            guild = tse.GuildAdapter(ctx.guild)
            seed.update(guild=guild, server=guild)
        seed_variables.update(seed)

        output = tag.run(self.engine, seed_variables=seed_variables, **kwargs)
        await tag.update_config()
        to_gather = []
        command_messages = []
        content = output.body[:2000] if output.body else None
        actions = output.actions
        embed = actions.get("embed")
        destination = ctx.channel
        replying = False

        if actions:
            try:
                await self.validate_checks(ctx, actions)
            except RequireCheckFailure as error:
                response = error.response
                if response is not None:
                    if response.strip():
                        await ctx.send(response[:2000])
                else:
                    start_adding_reactions(ctx.message, ["❌"])
                return

            if delete := actions.get("delete", False):
                to_gather.append(self.delete_quietly(ctx))

            if delete is False and (reactu := actions.get("reactu")):
                to_gather.append(self.do_reactu(ctx, reactu))

            if actions.get("commands"):
                for command in actions["commands"]:
                    if command.startswith("tag") or command == "invoketag":
                        await ctx.send("Tag looping isn't allowed.")
                        return
                    new = copy(ctx.message)
                    new.content = ctx.prefix + command
                    command_messages.append(new)

            if target := actions.get("target"):
                if target == "dm":
                    destination = await ctx.author.create_dm()
                elif target == "reply":
                    replying = True
                else:
                    try:
                        chan = await self.channel_converter.convert(ctx, target)
                    except commands.BadArgument:
                        pass
                    else:
                        if chan.permissions_for(ctx.me).send_messages:
                            destination = chan

        # this is going to become an asynchronous swamp
        msg = None
        if content or embed is not None:
            msg = await self.send_tag_response(ctx, destination, replying, content, embed=embed)
            if msg and (react := actions.get("react")):
                to_gather.append(self.do_reactions(ctx, react, msg))
        if command_messages:
            silent = actions.get("silent", False)
            overrides = actions.get("overrides")
            to_gather.append(self.process_commands(command_messages, silent, overrides))

        if to_gather:
            await asyncio.gather(*to_gather)

    async def send_tag_response(
        self,
        ctx: commands.Context,
        destination: discord.abc.Messageable,
        replying: bool,
        content: str = None,
        **kwargs,
    ) -> Optional[discord.Message]:
        if replying:
            try:
                return await ctx.reply(content, **kwargs)
            except discord.HTTPException:
                return await send_quietly(destination, content, **kwargs)
        else:
            return await send_quietly(destination, content, **kwargs)

    async def process_commands(
        self, messages: List[discord.Message], silent: bool, overrides: dict
    ):
        command_tasks = []
        for message in messages:
            command_task = asyncio.create_task(self.process_command(message, silent, overrides))
            command_tasks.append(command_task)
            await asyncio.sleep(0.1)
        await asyncio.gather(*command_tasks)

    async def process_command(
        self, command_message: discord.Message, silent: bool, overrides: dict
    ):
        ctx = await self.bot.get_context(
            command_message, cls=SilentContext if silent else commands.Context
        )

        if ctx.valid:
            if overrides:
                command = copy(ctx.command)
                # command = commands.Command()
                # command = ctx.command.copy() # does not work as it makes ctx a regular argument
                requires: Requires = copy(command.requires)
                priv_level = requires.privilege_level
                if priv_level not in (
                    PrivilegeLevel.NONE,
                    PrivilegeLevel.BOT_OWNER,
                    PrivilegeLevel.GUILD_OWNER,
                ):
                    if overrides["admin"] and priv_level is PrivilegeLevel.ADMIN:
                        requires.privilege_level = PrivilegeLevel.NONE
                    elif overrides["mod"] and priv_level is PrivilegeLevel.MOD:
                        requires.privilege_level = PrivilegeLevel.NONE
                if overrides["permissions"] and requires.user_perms:
                    requires.user_perms = discord.Permissions.none()
                command.requires = requires
                ctx.command = command
            await self.bot.invoke(ctx)

    async def validate_checks(self, ctx: commands.Context, actions: dict):
        to_gather = []
        if requires := actions.get("requires"):
            to_gather.append(self.validate_requires(ctx, requires))
        if blacklist := actions.get("blacklist"):
            to_gather.append(self.validate_blacklist(ctx, blacklist))
        if to_gather:
            await asyncio.gather(*to_gather)

    async def validate_requires(self, ctx: commands.Context, requires: dict):
        for argument in requires["items"]:
            role_or_channel = await self.role_or_channel_convert(ctx, argument)
            if not role_or_channel:
                continue
            if (
                isinstance(role_or_channel, discord.Role)
                and role_or_channel in ctx.author.roles
                or not isinstance(role_or_channel, discord.Role)
                and role_or_channel == ctx.channel
            ):
                return
        raise RequireCheckFailure(requires["response"])

    async def validate_blacklist(self, ctx: commands.Context, blacklist: dict):
        for argument in blacklist["items"]:
            role_or_channel = await self.role_or_channel_convert(ctx, argument)
            if not role_or_channel:
                continue
            if (
                isinstance(role_or_channel, discord.Role)
                and role_or_channel in ctx.author.roles
                or not isinstance(role_or_channel, discord.Role)
                and role_or_channel == ctx.channel
            ):
                raise RequireCheckFailure(blacklist["response"])

    async def role_or_channel_convert(self, ctx: commands.Context, argument: str):
        objects = await asyncio.gather(
            self.role_converter.convert(ctx, argument),
            self.channel_converter.convert(ctx, argument),
            return_exceptions=True,
        )
        objects = [obj for obj in objects if isinstance(obj, (discord.Role, discord.TextChannel))]
        return objects[0] if objects else None

    async def do_reactu(self, ctx: commands.Context, reactu: list):
        if reactu:
            for arg in reactu:
                try:
                    arg = await self.emoji_converter.convert(ctx, arg)
                except commands.BadArgument:
                    pass
                try:
                    await ctx.message.add_reaction(arg)
                except discord.HTTPException:
                    pass

    async def do_reactions(self, ctx: commands.Context, react: list, msg: discord.Message):
        if msg and react:
            for arg in react:
                try:
                    arg = await self.emoji_converter.convert(ctx, arg)
                except commands.BadArgument:
                    pass
                try:
                    await msg.add_reaction(arg)
                except discord.HTTPException:
                    pass

    @staticmethod
    async def delete_quietly(ctx: commands.Context):
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass
