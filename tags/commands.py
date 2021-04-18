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

from typing import Optional, Set, Dict, List
from urllib.parse import quote_plus

import discord
from redbot.core import commands
from redbot.core.commands import Requires, PrivilegeLevel
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import humanize_list, pagify, inline
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu, start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate, MessagePredicate
import TagScriptEngine as tse
import bs4

from .converters import TagConverter, TagName, TagScriptConverter, GlobalTagConverter
from .objects import Tag
from .errors import *

TAG_GUILD_LIMIT = 250
TAG_GLOBAL_LIMIT = 250

class Commands:
    @staticmethod
    def generate_tag_list(tags: Set[Tag]) -> Dict[str, List[str]]:
        aliases = []
        description = []

        for tag in tags:
            aliases.extend(tag.aliases)
            tagscript = tag.tagscript
            if len(tagscript) > 23:
                tagscript = tagscript[:20] + "..."
            tagscript = tagscript.replace("\n", " ")
            description.append(f"`{tag}` - {escape_markdown(tagscript)}")

        return {"aliases": aliases, "description": description}

    @commands.command(usage="<tag_name> [args]")
    async def invoketag(
        self, ctx: commands.Context, response: Optional[bool], tag_name: str, *, args: Optional[str] = ""
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

    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def tags(self, ctx: commands.Context):
        """View all tags and aliases in a server, or all global tags if this command is run in DMs."""
        guild = ctx.guild
        path = self.guild_tag_cache[guild.id] if guild else self.global_tag_cache
        if not path:
            return await ctx.send("This server has no tags." if guild else "No global tags have been added.")
    
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
        await menu(ctx, embeds, DEFAULT_CONTROLS)

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
        self, ctx: commands.Context, tag_name: TagName(allow_named_tags=True), *, tagscript: TagScriptConverter
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
            await ctx.send(await tag.edit_tagscript(tagscript))
            return

        tag = Tag(self, tag_name, tagscript, author_id=ctx.author.id, guild_id=ctx.guild.id)
        tag.add_to_cache()
        await tag.update_config()
        await ctx.send(f"Tag `{tag}` added.")

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command(name="alias")
    async def tag_alias(self, ctx: commands.Context, tag: TagConverter, alias: TagName):
        """Add an alias for a tag."""
        await ctx.send(await tag.add_alias(alias))

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command(name="unalias")
    async def tag_unalias(self, ctx: commands.Context, tag: TagConverter, alias: TagName(allow_named_tags=True)):
        """Remove an alias for a tag."""
        await ctx.send(await tag.remove_alias(alias))

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command(name="edit", aliases=["e"])
    async def tag_edit(
        self, ctx: commands.Context, tag: TagConverter, *, tagscript: TagScriptConverter
    ):
        """Edit a tag with TagScript."""
        await ctx.send(await tag.edit_tagscript(tagscript))

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command(name="remove", aliases=["delete", "-"])
    async def tag_remove(self, ctx: commands.Context, tag: TagConverter):
        """Delete a tag."""
        await ctx.send(await tag.delete())

    @tag.command(name="info")
    async def tag_info(self, ctx: commands.Context, tag: TagConverter):
        """Get info about a tag that is stored on this server."""
         await tag.send_info(ctx)

    @tag.command(name="raw")
    async def tag_raw(self, ctx: commands.Context, tag: TagConverter):
        """Get a tag's raw content."""
        await tag.send_raw_tagscript(ctx)

    @tag.command(name="list")
    async def tag_list(self, ctx: commands.Context):
        """View stored tags."""
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
        await menu(ctx, embeds, DEFAULT_CONTROLS)

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
            await ctx.send(await tag.edit_tagscript(tagscript))
            return

        tag = Tag(self, tag_name, tagscript, author_id=ctx.author.id)
        tag.add_to_cache()
        await tag.update_config()
        await ctx.send(f"Global tag `{tag}` added.")

    @tag_global.command(name="alias")
    async def tag_global_alias(self, ctx: commands.Context, tag: GlobalTagConverter, alias: TagName):
        """Add an alias for a global tag."""
        await ctx.send(await tag.add_alias(alias))

    @tag_global.command(name="unalias")
    async def tag_global_unalias(self, ctx: commands.Context, tag: GlobalTagConverter, alias: TagName(allow_named_tags=True)):
        """Remove an alias for a global tag."""
        await ctx.send(await tag.remove_alias(alias))

    @tag_global.command(name="edit", aliases=["e"])
    async def tag_global_edit(
        self,
        ctx: commands.Context,
        tag: GlobalTagConverter,
        *,
        tagscript: TagScriptConverter,
    ):
        """Edit a global tag with TagScript."""
        await ctx.send(await tag.edit_tagscript(tagscript))

    @tag_global.command(name="remove", aliases=["delete", "-"])
    async def tag_global_remove(
        self, ctx: commands.Context, tag: GlobalTagConverter
    ):
        """Delete a global tag."""
        await ctx.send(await tag.delete())

    @tag_global.command(name="info")
    async def tag_global_info(
        self, ctx: commands.Context, tag: GlobalTagConverter
    ):
        """Get info about a global tag."""
        await tag.send_info(ctx)

    @tag_global.command(name="raw")
    async def tag_global_raw(
        self, ctx: commands.Context, tag: TagConverter(check_global=True, global_priority=True)
    ):
        """Get a tag's raw content."""
        await tag.send_raw_tagscript(ctx)

    @tag_global.command(name="list")
    async def tag_global_list(self, ctx: commands.Context):
        """View stored tags."""
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
                tag.add_to_cache()
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
            tag.add_to_cache()
            await global_tag.update_config()
            migrated_global_alias += 1
        await ctx.send(
            f"Migrated {migrated_global_alias} global aliases to tags. "
            "Migration completed, unload the alias cog to prevent command "
            f"duplication with `{ctx.clean_prefix}unload alias`."
        )
