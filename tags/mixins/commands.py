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
import re
import time
import types
from collections import Counter
from typing import Dict, List, Optional, Set, Union
from urllib.parse import quote_plus

import discord
import TagScriptEngine as tse
from redbot.core import commands
from redbot.core.utils.chat_formatting import box, humanize_list, inline, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu, start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate
from tabulate import tabulate

from ..abc import MixinMeta
from ..converters import (
    GlobalTagConverter,
    GuildTagConverter,
    PastebinConverter,
    TagConverter,
    TagName,
    TagScriptConverter,
)
from ..doc_parser import SphinxObjectFileReader, parse_object_inv
from ..errors import TagFeedbackError
from ..objects import Tag
from ..utils import chunks, get_menu

TAG_GUILD_LIMIT = 250
TAG_GLOBAL_LIMIT = 250

TAG_RE = re.compile(r"(?i)(\[p\])?\btag'?s?\b")

DOCS_URL = "https://phen-cogs.readthedocs.io/en/latest"

log = logging.getLogger("red.phenom4n4n.tags.commands")


def _sub(match: re.Match) -> str:
    if match.group(1):
        return "[p]tag global"

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
    @staticmethod
    def generate_tag_list(tags: Set[Tag]) -> Dict[str, List[str]]:
        aliases = []
        description = []

        for tag in tags:
            aliases.extend(tag.aliases)
            tagscript = tag.tagscript.replace("\n", " ")
            if len(tagscript) > 23:
                tagscript = tagscript[:20] + "..."
            tagscript = discord.utils.escape_markdown(tagscript)
            description.append(f"`{tag}` - {tagscript}")

        return {"aliases": aliases, "description": description}

    @commands.command(usage="<tag_name> [args]")
    async def invoketag(
        self,
        ctx: commands.Context,
        response: Optional[bool],
        tag_name: str,
        *,
        args: Optional[str] = "",
    ):
        """
        Manually invoke a tag with its name and arguments.

        Restricting this command with permissions in servers will restrict all members from invoking tags.

        **Examples:**
        `[p]invoketag searchitem trophy`
        `[p]invoketag donate`
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

    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def tags(self, ctx: commands.Context):
        """
        View all tags and aliases.

        This command will show global tags if run in DMs.

        **Example:**
        `[p]tags`
        """
        guild = ctx.guild
        path = self.guild_tag_cache[guild.id] if guild else self.global_tag_cache
        if not path:
            return await ctx.send(
                "This server has no tags." if guild else "No global tags have been added."
            )

        tags = path.keys()
        title = f"Tags in {guild}" if guild else "Global Tags"
        embed = discord.Embed(color=await ctx.embed_color(), title=title)
        footer = f"{len(tags)} tags"
        embeds = []

        description = humanize_list([inline(tag) for tag in tags])
        pages = list(pagify(description))
        for index, page in enumerate(pages, 1):
            e = embed.copy()
            e.description = page
            e.set_footer(text=f"{index}/{len(pages)} | {footer}")
            embeds.append(e)
        await get_menu()(ctx, embeds, DEFAULT_CONTROLS)

    def validate_tag_count(self, guild: discord.Guild):
        tag_count = len(self.get_unique_tags(guild))
        if guild:
            if tag_count >= TAG_GUILD_LIMIT:
                raise TagFeedbackError(
                    f"This server has reached the limit of **{TAG_GUILD_LIMIT}** tags."
                )
        elif tag_count >= TAG_GLOBAL_LIMIT:
            raise TagFeedbackError(
                f"You have reached the limit of **{TAG_GLOBAL_LIMIT}** global tags."
            )

    async def create_tag(
        self, ctx: commands.Context, tag_name: str, tagscript: str, *, global_tag: bool = False
    ):
        kwargs = {"author_id": ctx.author.id}

        if global_tag:
            guild = None
            tag = self.get_tag(None, tag_name, global_priority=True)
        else:
            guild = ctx.guild
            tag = self.get_tag(guild, tag_name, check_global=False)
            kwargs["guild_id"] = guild.id
        self.validate_tag_count(guild)

        if tag:
            tag_prefix = tag.name_prefix
            msg = await ctx.send(
                f"`{tag_name}` is already a registered {tag_prefix.lower()}. Would you like to overwrite it?"
            )
            start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
            pred = ReactionPredicate.yes_or_no(msg, ctx.author)
            try:
                await ctx.bot.wait_for("reaction_add", check=pred, timeout=30)
            except asyncio.TimeoutError:
                return await ctx.send(f"{tag_prefix} edit cancelled.")

            if pred.result is False:
                return await ctx.send(f"{tag_prefix} edit cancelled.")
            await ctx.send(await tag.edit_tagscript(tagscript))
            return

        tag = Tag(self, tag_name, tagscript, **kwargs)
        await ctx.send(await tag.initialize())

    @commands.guild_only()
    @commands.group(aliases=["customcom", "cc", "alias"])
    async def tag(self, ctx: commands.Context):
        """
        Tag management with TagScript.

        These commands use TagScriptEngine.
        Read the [TagScript documentation](https://phen-cogs.readthedocs.io/en/latest/) to learn how to use TagScript blocks.
        """

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command("add", aliases=["create", "+"])
    async def tag_add(
        self,
        ctx: commands.Context,
        tag_name: TagName(allow_named_tags=True),
        *,
        tagscript: TagScriptConverter,
    ):
        """
        Add a tag with TagScript.

        [Tag usage guide](https://phen-cogs.readthedocs.io/en/latest/tags/blocks.html#usage)

        **Example:**
        `[p]tag add lawsofmotion {embed(title):Newton's Laws of motion}
        {embed(description): According to all known laws of aviation, there is no way a bee should be able to fly.}`
        """
        await self.create_tag(ctx, tag_name, tagscript)

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command("pastebin", aliases=["++"])
    async def tag_pastebin(
        self,
        ctx: commands.Context,
        tag_name: TagName(allow_named_tags=True),
        *,
        link: PastebinConverter,
    ):
        """
        Add a tag with a Pastebin link.

        **Example:**
        `[p]tag pastebin starwarsopeningcrawl https://pastebin.com/CKjn6uYv`
        """
        await self.create_tag(ctx, tag_name, link)

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command("alias")
    async def tag_alias(self, ctx: commands.Context, tag: GuildTagConverter, alias: TagName):
        """
                Add an alias for a tag.

                Adding an alias to the tag will make the tag invokable using the alias or the tag name.
                In the example below, running `[p]donation` will invoke the `donate` tag.
        ​
                **Example:**
                `[p]tag alias donate donation`
        """
        await ctx.send(await tag.add_alias(alias))

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command("unalias")
    async def tag_unalias(
        self, ctx: commands.Context, tag: GuildTagConverter, alias: TagName(allow_named_tags=True)
    ):
        """
        Remove an alias for a tag.

        ​The tag will still be able to be used under its original name.
        You can delete the original tag with the `[p]tag remove` command.

        **Example:**
        `tag unalias donate donation`
        """
        await ctx.send(await tag.remove_alias(alias))

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command("edit", aliases=["e"])
    async def tag_edit(
        self, ctx: commands.Context, tag: GuildTagConverter, *, tagscript: TagScriptConverter
    ):
        """
        Edit a tag's TagScript.

        The passed tagscript will replace the tag's current tagscript.
        View the [TagScript docs](https://phen-cogs.readthedocs.io/en/latest/blocks.html) to find information on how to write valid tagscript.

        **Example:**
        `[p]tag edit rickroll Never gonna give you up!`
        """
        await ctx.send(await tag.edit_tagscript(tagscript))

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command("append")
    async def tag_append(
        self, ctx: commands.Context, tag: GuildTagConverter, *, tagscript: TagScriptConverter
    ):
        """
        Add text to a tag's TagScript.

        **Example:**
        `[p]tag append rickroll Never gonna let you down!`
        """
        await ctx.send(await tag.append_tagscript(tagscript))

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command("remove", aliases=["delete", "-"])
    async def tag_remove(self, ctx: commands.Context, tag: GuildTagConverter):
        """
        Permanently delete a tag.

        If you want to remove a tag's alias, use `[p]tag unalias`.

        **Example:**
        `[p]tag remove RickRoll`
        """
        await ctx.send(await tag.delete())

    @tag.command("info")
    async def tag_info(self, ctx: commands.Context, tag: TagConverter):
        """
        Show information about a tag.

        You can view meta information for a tag on this server or a global tag.
        If a tag on this server has the same name as a global tag, it will show the server tag.

        **Example:**
        `[p]tag info notsupport`
        """
        await tag.send_info(ctx)

    @tag.command("raw")
    async def tag_raw(self, ctx: commands.Context, tag: GuildTagConverter):
        """
        Get a tag's raw content.

        The sent TagScript will be escaped from Discord style formatting characters.

        **Example:**
        `[p]tag raw noping`
        """
        await tag.send_raw_tagscript(ctx)

    @tag.command("list")
    async def tag_list(self, ctx: commands.Context):
        """
        View all stored tags on this server.

        To view info on a specific tag, use `[p]tag info`.

        **Example:**
        `[p]tag list`
        """
        tags = self.get_unique_tags(ctx.guild)
        if not tags:
            return await ctx.send("There are no stored tags on this server.")

        data = self.generate_tag_list(tags)
        aliases = data["aliases"]
        description = data["description"]

        e = discord.Embed(color=await ctx.embed_color())
        e.set_author(name="Stored Tags", icon_url=ctx.guild.icon_url)

        embeds = []
        pages = list(pagify("\n".join(description)))
        footer = f"{len(tags)} tags | {len(aliases)} aliases"
        for index, page in enumerate(pages, 1):
            embed = e.copy()
            embed.description = page
            embed.set_footer(text=f"{index}/{len(pages)} | {footer}")
            embeds.append(embed)
        await get_menu()(ctx, embeds, DEFAULT_CONTROLS)

    async def doc_fetch(self):
        async with self.session.get(f"{DOCS_URL}/objects.inv") as response:
            inv = SphinxObjectFileReader(await response.read())
        self.docs = parse_object_inv(inv, DOCS_URL)

    async def doc_search(self, keyword: str) -> Dict[str, str]:
        keyword = keyword.lower()
        if not self.docs:
            await self.doc_fetch()
        return {key: value for key, value in self.docs.items() if keyword in key.lower()}

    async def show_tag_usage(self, ctx: commands.Context, guild: discord.Guild = None):
        tags = self.get_unique_tags(guild)
        if not tags:
            message = "This server has no tags" if guild else "There are no global tags."
            return await ctx.send(message)
        counter = Counter({tag.name: tag.uses for tag in tags})
        e = discord.Embed(title="Tag Stats", color=await ctx.embed_color())
        embeds = []
        for usage_data in chunks(counter.most_common(), 10):
            usage_chart = box(tabulate(usage_data, headers=("Tag", "Uses")), "prolog")
            embed = e.copy()
            embed.description = usage_chart
            embeds.append(embed)
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @tag.command("usage", aliases=["stats"])
    async def tag_usage(self, ctx: commands.Context):
        """
        See tag usage stats.

        **Example:**
        `[p]tag usage`
        """
        await self.show_tag_usage(ctx, ctx.guild)

    @tag.command("docs")
    async def tag_docs(self, ctx: commands.Context, keyword: str = None):
        """
        Search the TagScript documentation for a block.

        https://phen-cogs.readthedocs.io/en/latest/

        **Example:**
        `[p]tag docs embed`
        """
        await ctx.trigger_typing()
        e = discord.Embed(color=await ctx.embed_color(), title="Tags Documentation")
        if keyword:
            matched_labels = await self.doc_search(keyword)
            description = [f"Search for: `{keyword}`"]
            for name, url in matched_labels.items():
                description.append(f"[`{name}`]({url})")
            url = f"{DOCS_URL}/search.html?q={quote_plus(keyword)}&check_keywords=yes&area=default"
            e.url = url
            embeds = []
            description = "\n".join(description)
            for page in pagify(description):
                embed = e.copy()
                embed.description = page
                embeds.append(embed)
            await get_menu()(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e.url = DOCS_URL
            await ctx.send(embed=e)

    @commands.is_owner()
    @tag.command("run", aliases=["execute"])
    async def tag_run(self, ctx: commands.Context, *, tagscript: str):
        """
        Execute TagScript without storing.

        The variables and actions fields display debugging information.

        **Example:**
        `[p]tag run {#:yes,no}`
        """
        start = time.monotonic()
        seed = self.get_seed_from_context(ctx)
        output = self.engine.process(
            tagscript, seed_variables=seed, dot_parameter=self.dot_parameter
        )
        if self.async_enabled:
            output = await output
        end = time.monotonic()
        actions = output.actions

        content = output.body[:2000] if output.body else None
        await self.send_tag_response(ctx, actions, content)

        e = discord.Embed(
            color=await ctx.embed_color(),
            title="TagScriptEngine",
            description=f"Executed in **{round((end - start) * 1000, 3)}** ms",
        )
        for page in pagify(tagscript, page_length=1024):
            e.add_field(name="Input", value=page, inline=False)
        if actions:
            e.add_field(name="Actions", value=actions, inline=False)
        if output.variables:
            variables = "\n".join(
                f"`{name}`: {type(adapter).__name__}" for name, adapter in output.variables.items()
            )
            for page in pagify(variables, page_length=1024):
                e.add_field(name="Variables", value=page, inline=False)

        await ctx.send(embed=e)

    @commands.is_owner()
    @tag.command("process")
    async def tag_process(self, ctx: commands.Context, *, tagscript: str):
        """
        Process a temporary Tag without storing.

        This differs from `[p]tag run` as it creates a fake tag and properly handles actions for all blocks.
        The `{args}` block is not supported.

        **Example:**
        `[p]tag run {require(Admin):You must be admin to use this tag.} Congrats on being an admin!`
        """
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
    @tag.group("global")
    @copy_doc(tag)
    async def tag_global(self, ctx: commands.Context):
        pass

    @tag_global.command("add", aliases=["create", "+"])
    @copy_doc(tag_add)
    async def tag_global_add(
        self,
        ctx: commands.Context,
        tag_name: TagName(global_priority=True),
        *,
        tagscript: TagScriptConverter,
    ):
        await self.create_tag(ctx, tag_name, tagscript, global_tag=True)

    @tag_global.command("pastebin", aliases=["++"])
    @copy_doc(tag_pastebin)
    async def tag_global_pastebin(
        self,
        ctx: commands.Context,
        tag_name: TagName(global_priority=True),
        *,
        link: PastebinConverter,
    ):
        await self.create_tag(ctx, tag_name, link, global_tag=True)

    @tag_global.command("alias")
    @copy_doc(tag_alias)
    async def tag_global_alias(
        self, ctx: commands.Context, tag: GlobalTagConverter, alias: TagName
    ):
        await ctx.send(await tag.add_alias(alias))

    @tag_global.command("unalias")
    @copy_doc(tag_unalias)
    async def tag_global_unalias(
        self, ctx: commands.Context, tag: GlobalTagConverter, alias: TagName(allow_named_tags=True)
    ):
        await ctx.send(await tag.remove_alias(alias))

    @tag_global.command("edit", aliases=["e"])
    @copy_doc(tag_edit)
    async def tag_global_edit(
        self,
        ctx: commands.Context,
        tag: GlobalTagConverter,
        *,
        tagscript: TagScriptConverter,
    ):
        await ctx.send(await tag.edit_tagscript(tagscript))

    @tag_global.command("append")
    @copy_doc(tag_append)
    async def tag_global_append(
        self, ctx: commands.Context, tag: GlobalTagConverter, *, tagscript: TagScriptConverter
    ):
        await ctx.send(await tag.append_tagscript(tagscript))

    @tag_global.command("remove", aliases=["delete", "-"])
    @copy_doc(tag_remove)
    async def tag_global_remove(self, ctx: commands.Context, tag: GlobalTagConverter):
        await ctx.send(await tag.delete())

    @tag_global.command("raw")
    @copy_doc(tag_raw)
    async def tag_global_raw(self, ctx: commands.Context, tag: GlobalTagConverter):
        await tag.send_raw_tagscript(ctx)

    @tag_global.command("list")
    @copy_doc(tag_list)
    async def tag_global_list(self, ctx: commands.Context):
        tags = self.get_unique_tags()
        if not tags:
            return await ctx.send("There are no global tags.")

        data = self.generate_tag_list(tags)
        aliases = data["aliases"]
        description = data["description"]

        e = discord.Embed(color=await ctx.embed_color())
        e.set_author(name="Global Tags", icon_url=ctx.me.avatar_url)

        embeds = []
        pages = list(pagify("\n".join(description)))
        footer = f"{len(tags)} tags | {len(aliases)} aliases"
        for index, page in enumerate(pages, 1):
            embed = e.copy()
            embed.description = page
            embed.set_footer(text=f"{index}/{len(pages)} | {footer}")
            embeds.append(embed)
        await get_menu()(ctx, embeds, DEFAULT_CONTROLS)

    @tag_global.command("usage", aliases=["stats"])
    @copy_doc(tag_usage)
    async def tag_global_usage(self, ctx: commands.Context):
        await self.show_tag_usage(ctx)
