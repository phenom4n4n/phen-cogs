from TagScriptEngine import block, Interpreter, adapter
from typing import Literal, Optional
import discord
from discord.utils import escape_markdown
import time
import re
from copy import copy
import asyncio

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.predicates import ReactionPredicate
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS, start_adding_reactions, close_menu
from redbot.core.utils.chat_formatting import pagify, humanize_list, box

from .converters import tag_name

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

COM_RE = re.compile(r"{(?:c|com|command): ?(\S+)}")


class Tags(commands.Cog):
    """
    Create and use tags.
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=567234895692346562369,
            force_registration=True,
        )
        default_guild = {"tags": {}}
        self.config.register_guild(**default_guild)
        blocks = [
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

    @commands.group(invoke_without_command=True, usage="<tag_name> [args]")
    async def tag(self, ctx, response: Optional[bool], tag_name: tag_name, *, args: str = "None"):
        """Tag management with TagScript.

        These commands use TagScriptEngine. [This site](https://github.com/JonSnowbd/TagScript/blob/v2/Documentation/Using%20TSE.md) has documentation on how to use TagScript blocks."""
        if response is None:
            response = True
        tag_data = await self.get_stored_tag(ctx, tag_name, response)
        if tag_data:
            tag = tag_data["tag"]
            query = tag.replace("{args}", args)
            output = self.engine.process(query)
            result = output.body[:2000]
            if result:
                await ctx.send(result)
            async with self.config.guild(ctx.guild).tags() as t:
                t[tag_name]["uses"] += 1

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command()
    async def add(self, ctx, tag_name: tag_name, *, tagscript):
        """Add a tag with TagScript."""
        command = self.bot.get_command(tag_name)
        if command:
            await ctx.send(f"`{tag_name}` is already a registered command.")
            return

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
    @tag.command()
    async def edit(self, ctx, tag_name: tag_name, *, tagscript):
        """Edit a tag with TagScript."""
        tag = await self.get_stored_tag(ctx, tag_name, False)
        if not tag:
            return

        await self.store_tag(ctx, tag_name, tagscript)

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command(aliases=["delete"])
    async def remove(self, ctx, tag_name: tag_name):
        """Delete a tag."""
        tag = await self.get_stored_tag(ctx, tag_name)
        if tag:
            async with self.config.guild(ctx.guild).tags() as e:
                del e[tag_name]
            await ctx.send("Tag deleted.")

    @tag.command(name="info")
    async def tag_info(self, ctx, name: str):
        """Get info about an tag that is stored on this server."""
        tag = await self.get_stored_tag(ctx, name)
        if tag:
            e = discord.Embed(
                color=await ctx.embed_color(),
                title=f"`{name}` Info",
                description=f"Author: <@!{tag['author']}>\nUses: {tag['uses']}\nLength: {len(tag['tag'])}",
            )
            e.add_field(name="TagScript", value=box(tag["tag"]))
            e.set_author(name=ctx.guild, icon_url=ctx.guild.icon_url)
            await ctx.send(embed=e)

    @tag.command(name="raw")
    async def tag_raw(self, ctx, name: str):
        """Get a tag's raw content."""
        tag = await self.get_stored_tag(ctx, name)
        if tag:
            await ctx.send(
                escape_markdown(tag["tag"]),
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
    async def run(self, ctx, *, tagscript):
        """Execute TagScript without storing."""
        start = time.monotonic()
        output = self.engine.process(tagscript)
        end = time.monotonic()

        e = discord.Embed(
            color=await ctx.embed_color(),
            title="TagScriptEngine",
            description=f"Executed in **{round((end - start) * 1000, 3)}** ms",
        )
        e.add_field(name="Input", value=tagscript, inline=False)
        if output.actions:
            e.add_field(name="Actions", value=output.actions)
        if output.variables:
            e.add_field(name="Variables", value=output.variables)
        e.add_field(name="Output", value=output.body or discord.Embed.Empty, inline=False)

        m = await ctx.send(embed=e)

    @commands.is_owner()
    @tag.command()
    async def process(self, ctx: commands.Context, *, tagscript: str):
        """Process TagScript without storing."""
        await self.process_tag(ctx, tagscript, "")

    async def store_tag(self, ctx: commands.Context, name: str, tagscript: str):
        async with self.config.guild(ctx.guild).tags() as t:
            t[name] = {"author": ctx.author.id, "uses": 0, "tag": tagscript}
        await ctx.send(f"Tag stored under the name `{name}`.")

    async def get_stored_tag(self, ctx: commands.Context, name: tag_name, response: bool = True):
        tags = await self.config.guild(ctx.guild).tags()
        try:
            tag = tags[name]
        except KeyError:
            if response:
                await ctx.send(f'Tag "{name}" not found.')
            return
        return tag

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot or not (
            message.guild and await self.bot.message_eligible_as_command(message)
        ):
            return
        ctx = await self.bot.get_context(message)
        if ctx.prefix is None:
            return

        tag_command = message.content.lstrip(ctx.prefix)
        tag_split = tag_command.split(" ")
        if not tag_split:
            return
        tag_name = tag_split[0]
        tag = await self.get_stored_tag(ctx, tag_name, False)
        if tag:
            new_message = copy(message)
            new_message.content = f"{ctx.prefix}tag False {tag_command}"
            await self.bot.process_commands(new_message)

    async def process_tag(self, ctx: commands.Context, tagscript: str, args: str) -> str:
        output = self.engine.process(tagscript)
        if output.body:
            o = output.body.replace("{args}", args)
            commands = COM_RE.findall(o)
            to_process = []
            if commands:
                o = COM_RE.sub(o, "")
                for command in commands:
                    new = copy(ctx.message)
                    new.content = ctx.prefix + command
                    to_process.append(self.bot.process_commands(new))
            if o:
                await ctx.send(o)
            await asyncio.gather(to_process)
