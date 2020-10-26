import asyncio
import time
from copy import copy
from typing import Literal, Optional

import logging
import discord
from discord.utils import escape_markdown
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import box, humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, close_menu, menu, start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate
from TagScriptEngine import Interpreter, adapter, block

from .blocks import stable_blocks
from .converters import TagConverter, TagName
from .objects import Tag
from .adapters import MemberAdapter, TextChannelAdapter, GuildAdapter

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

log = logging.getLogger("redbot.phenom4n4n.tags")


async def delete_quietly(message: discord.Message):
    try:
        await message.delete()
    except discord.HTTPException:
        pass


class Tags(commands.Cog):
    """
    Create and use tags.

    The TagScript documentation can be found [here](https://github.com/phenom4n4n/phen-cogs/blob/master/tags/README.md).
    """

    __version__ = "1.2.2"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\nCog Version: {self.__version__}"

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        cog = self.bot.get_cog("CustomCommands")
        if cog:
            raise RuntimeError(
                "This cog conflicts with CustomCommands and cannot be loaded with both at the same time."
            )
        self.config = Config.get_conf(
            self,
            identifier=567234895692346562369,
            force_registration=True,
        )
        default_guild = {"tags": {}}
        self.config.register_guild(**default_guild)
        blocks = stable_blocks + [
            block.MathBlock(),
            block.RandomBlock(),
            block.RangeBlock(),
            block.AnyBlock(),
            block.IfBlock(),
            block.AllBlock(),
            block.BreakBlock(),
            block.StrfBlock(),
            block.StopBlock(),
            block.AssignmentBlock(),
            block.FiftyFiftyBlock(),
            block.ShortCutRedirectBlock("message"),
            block.LooseVariableGetterBlock(),
            block.SubstringBlock(),
        ]
        self.engine = Interpreter(blocks)

    async def red_delete_data_for_user(self, *, requester: str, user_id: int):
        guilds_data = await self.config.all_guilds()
        for guild_id, data in guilds_data.items():
            guild = self.bot.get_guild(guild_id)
            if guild and data["tags"]:
                for name, tag in data["tags"].items():
                    if str(user_id) in str(tag["author"]):
                        async with self.config.guild(guild).tags() as t:
                            del t[name]

    @commands.guild_only()
    @commands.group(invoke_without_command=True, usage="<tag_name> [args]")
    async def tag(self, ctx, response: Optional[bool], tag_name: str, *, args: Optional[str] = ""):
        """Tag management with TagScript.

        These commands use TagScriptEngine. [This site](https://github.com/phenom4n4n/phen-cogs/blob/master/tags/README.md) has documentation on how to use TagScript blocks."""
        if response is None:
            response = True
        try:
            tag = await TagConverter().convert(ctx, tag_name)
        except commands.BadArgument as e:
            if response:
                await ctx.send(e)
                return
        async with self.config.guild(ctx.guild).tags() as t:
            t[tag_name]["uses"] += 1
        seed = {"args": adapter.StringAdapter(args)}
        await self.process_tag(ctx, tag, seed_variables=seed)

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command()
    async def add(self, ctx, tag_name: TagName, *, tagscript):
        """Add a tag with TagScript."""
        tag = await self.get_stored_tag(ctx, tag_name, False)
        if tag:
            msg = await ctx.send(
                f"`{tag_name}` is already registered tag. Would you like to overwrite it?"
            )
            start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
            pred = ReactionPredicate.yes_or_no(msg, ctx.author)
            await ctx.bot.wait_for("reaction_add", check=pred)

            if pred.result is False:
                await ctx.send("Action cancelled.")
                return

        await self.store_tag(ctx, tag_name, tagscript)

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command(aliases=["e"])
    async def edit(self, ctx, tag: TagConverter, *, tagscript):
        """Edit a tag with TagScript."""
        async with self.config.guild(ctx.guild).tags() as t:
            t[str(tag)]["tag"] = tagscript
        await ctx.send(f"Tag `{tag}` edited.")

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command(aliases=["delete"])
    async def remove(self, ctx, tag: TagConverter):
        """Delete a tag."""
        async with self.config.guild(ctx.guild).tags() as e:
            del e[str(tag)]
        await ctx.send("Tag deleted.")

    @tag.command(name="info")
    async def tag_info(self, ctx, tag: TagConverter):
        """Get info about an tag that is stored on this server."""
        e = discord.Embed(
            color=await ctx.embed_color(),
            title=f"`{tag}` Info",
            description=f"Author: {tag.author.mention if tag.author else tag.author_id}\nUses: {tag.uses}\nLength: {len(tag)}",
        )
        e.add_field(name="TagScript", value=box(str(tag)))
        e.set_author(name=ctx.guild, icon_url=ctx.guild.icon_url)
        await ctx.send(embed=e)

    @tag.command(name="raw")
    async def tag_raw(self, ctx, tag: TagConverter):
        """Get a tag's raw content."""
        await ctx.send(
            escape_markdown(tag.tagscript[:2000]),
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=False),
        )

    @tag.command(name="list")
    async def tag_list(self, ctx):
        """View stored tags."""
        tags = await self.config.guild(ctx.guild).tags()
        description = []

        for name, tag in tags.items():
            description.append(f"`{name}` - Created by <@!{tag['author']}>")
        description = "\n".join(description)

        color = await self.bot.get_embed_colour(ctx)
        e = discord.Embed(color=color, title=f"Stored Tags", description=description)
        e.set_author(name=ctx.guild, icon_url=ctx.guild.icon_url)
        await ctx.send(embed=e)

    @commands.is_owner()
    @commands.mod_or_permissions(manage_guild=True)
    @tag.command(aliases=["execute"])
    async def run(self, ctx: commands.Context, *, tagscript: str):
        """Execute TagScript without storing."""
        start = time.monotonic()
        author = MemberAdapter(ctx.author)
        target = MemberAdapter(ctx.message.mentions[0]) if ctx.message.mentions else author
        channel = TextChannelAdapter(ctx.channel)
        guild = GuildAdapter(ctx.guild)
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
                [f"{name}: {type(obj).__name__}" for name, obj in output.variables.items()]
            )
            e.add_field(name="Variables", value=vars, inline=False)
        e.add_field(name="Output", value=output.body or "NO OUTPUT", inline=False)

        await ctx.send(embed=e)

    @commands.is_owner()
    @tag.command()
    async def process(self, ctx: commands.Context, *, tagscript: str):
        """Process TagScript without storing."""
        tag = Tag(
            "processed_tag",
            tagscript,
            invoker=ctx.author,
            author=ctx.author,
            author_id=ctx.author.id,
            uses=1,
            ctx=ctx,
        )
        await self.process_tag(ctx, tag)

    async def store_tag(self, ctx: commands.Context, name: str, tagscript: str):
        async with self.config.guild(ctx.guild).tags() as t:
            t[name] = {"author": ctx.author.id, "uses": 0, "tag": tagscript}
        await ctx.send(f"Tag stored under the name `{name}`.")

    async def get_stored_tag(self, ctx: commands.Context, name: TagName, response: bool = True):
        tags = await self.config.guild(ctx.guild).tags()
        tag = tags.get(name)
        if tag:
            tag = Tag.from_dict(name, tag, ctx=ctx)
            return tag
        return None

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot or not (
            message.guild and await self.bot.message_eligible_as_command(message)
        ):
            return
        ctx = await self.bot.get_context(message)
        if ctx.prefix is None:
            return

        tag_command = message.content[len(ctx.prefix) :]
        tag_split = tag_command.split(" ")
        if not tag_split:
            return
        tag_name = tag_split[0]
        tag = await self.get_stored_tag(ctx, tag_name, False)
        if tag:
            new_message = copy(message)
            new_message.content = f"{ctx.prefix}tag False {tag_command}"
            if self.bot.user.id in [741074175875088424, 462364255128256513]:  # dev stuff lol
                print(f"Processing tag for {tag_name} on {message.guild}")
            await self.bot.process_commands(new_message)

    async def process_tag(
        self, ctx: commands.Context, tag: Tag, *, seed_variables: dict = {}, **kwargs
    ) -> str:
        author = MemberAdapter(ctx.author)
        target = MemberAdapter(ctx.message.mentions[0]) if ctx.message.mentions else author
        channel = TextChannelAdapter(ctx.channel)
        guild = GuildAdapter(ctx.guild)
        seed = {
            "author": author,
            "user": author,
            "target": target,
            "member": target,
            "channel": channel,
            "guild": guild,
            "server": guild,
        }
        seed_variables.update(seed)

        output = tag.run(self.engine, seed_variables=seed_variables, **kwargs)
        to_gather = []
        commands_to_process = []
        content = output.body[:2000] if output.body else None
        actions = output.actions
        embed = actions.get("embed")

        if actions:
            if actions.get("delete"):
                if ctx.channel.permissions_for(ctx.me).manage_messages:
                    await delete_quietly(ctx.message)
            if actions.get("commands"):
                for command in actions["commands"]:
                    if command.startswith("tag"):
                        await ctx.send("Looping isn't allowed.")
                        return
                    new = copy(ctx.message)
                    new.content = ctx.prefix + command
                    commands_to_process.append(self.bot.process_commands(new))

        if content or embed:
            try:
                await ctx.send(content, embed=embed)
            except discord.HTTPException:
                return await ctx.send(
                    "I failed to send that embed. The tag has stopped processing."
                )

        if to_gather:
            await asyncio.gather(*to_gather)
        if commands_to_process:
            await asyncio.gather(*commands_to_process)
