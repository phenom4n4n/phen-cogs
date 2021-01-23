import asyncio
import time
from copy import copy
from typing import Literal, Optional, Tuple

import logging
import discord
from discord.utils import escape_markdown
from redbot.core import commands
from redbot.core.commands import Requires, PrivilegeLevel
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import box, humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, close_menu, menu, start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate
from TagScriptEngine import Interpreter, adapter, block
from collections import defaultdict

from .blocks import stable_blocks
from .converters import TagConverter, TagName, TagScriptConverter
from .objects import Tag
from .adapters import MemberAdapter, TextChannelAdapter, GuildAdapter
from .ctx import SilentContext
from .errors import MissingTagPermissions

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

log = logging.getLogger("red.phenom4n4n.tags")


async def delete_quietly(message: discord.Message):
    try:
        await message.delete()
    except discord.HTTPException:
        pass


async def send_quietly(destination: discord.abc.Messageable, content: str = None, **kwargs):
    try:
        return await destination.send(content, **kwargs)
    except discord.HTTPException:
        pass


class Tags(commands.Cog):
    """
    Create and use tags.

    The TagScript documentation can be found [here](https://phen-cogs.readthedocs.io/en/latest/index.html).
    """

    __version__ = "1.4.7"

    def format_help_for_context(self, ctx: commands.Context):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\nCog Version: {self.__version__}"

    def __init__(self, bot: Red) -> None:
        self.bot = bot
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
            block.ShortCutRedirectBlock("args"),
            block.LooseVariableGetterBlock(),
            block.SubstringBlock(),
        ]
        self.engine = Interpreter(blocks)
        self.role_converter = commands.RoleConverter()
        self.channel_converter = commands.TextChannelConverter()
        self.member_converter = commands.MemberConverter()
        self.emoji_converter = commands.EmojiConverter()

        self.guild_tag_cache = defaultdict(dict)
        self.task = asyncio.create_task(self.cache_tags())

    def cog_unload(self):
        if self.task:
            self.task.cancel()

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
        await self.bot.wait_until_ready()
        guilds_data = await self.config.all_guilds()
        for guild_id, data in guilds_data.items():
            tags = data.get("tags", {})
            guild = self.bot.get_guild(guild_id) or discord.Object(guild_id)
            for tag_name, tag_data in tags.items():
                tag_object = Tag.from_dict(self, guild, tag_name, tag_data)
                self.guild_tag_cache[guild_id][tag_name] = tag_object
        log.debug("tag cache built")

    def get_tag(self, guild: discord.Guild, tag_name: str):
        return self.guild_tag_cache[guild.id].get(tag_name)

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

    @commands.guild_only()
    @commands.group(invoke_without_command=True, usage="<tag_name> [args]", aliases=["customcom"])
    async def tag(self, ctx, response: Optional[bool], tag_name: str, *, args: Optional[str] = ""):
        """
        Tag management with TagScript.

        These commands use TagScriptEngine. [This site](https://phen-cogs.readthedocs.io/en/latest/index.html) has documentation on how to use TagScript blocks.
        """
        if response is None:
            response = True
        try:
            _tag = await TagConverter().convert(ctx, tag_name)
        except commands.BadArgument as e:
            if response:
                await ctx.send(e)
            return
        seed = {"args": adapter.StringAdapter(args)}
        log.info(f"Processing tag for {tag_name} on {ctx.guild} ({ctx.guild.id})")
        await self.process_tag(ctx, _tag, seed_variables=seed)

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command(aliases=["create", "+"])
    async def add(
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

        tag = Tag(self, ctx.guild, tag_name, tagscript, author=ctx.author)
        self.guild_tag_cache[ctx.guild.id][tag_name] = tag
        async with self.config.guild(ctx.guild).tags() as t:
            t[tag_name] = tag.to_dict()
        await ctx.send(f"Tag `{tag}` added.")

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command(aliases=["e"])
    async def edit(
        self, ctx: commands.Context, tag: TagConverter, *, tagscript: TagScriptConverter
    ):
        """Edit a tag with TagScript."""
        tag.tagscript = tagscript
        await tag.update_config()
        await ctx.send(f"Tag `{tag}` edited.")
        # await self.cache_tags()

    @commands.mod_or_permissions(manage_guild=True)
    @tag.command(aliases=["delete", "-"])
    async def remove(self, ctx: commands.Context, tag: TagConverter):
        """Delete a tag."""
        async with self.config.guild(ctx.guild).tags() as e:
            del e[str(tag)]
        del self.guild_tag_cache[ctx.guild.id][str(tag)]
        await ctx.send("Tag deleted.")
        # await self.cache_tags()

    @tag.command(name="info")
    async def tag_info(self, ctx: commands.Context, tag: TagConverter):
        """Get info about an tag that is stored on this server."""
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
        await ctx.send(
            escape_markdown(tag.tagscript[:2000]),
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

        e = discord.Embed(color=await ctx.embed_color(), title=f"Stored Tags")
        e.set_author(name=ctx.guild, icon_url=ctx.guild.icon_url)

        embeds = []
        pages = list(pagify(description))
        for index, page in enumerate(pages, 1):
            embed = e.copy()
            embed.description = page
            embed.set_footer(text=f"{index}/{len(pages)}")
            embeds.append(embed)
        await menu(ctx, embeds, DEFAULT_CONTROLS)

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
            self,
            ctx.guild,
            "processed_tag",
            tagscript,
            author=ctx.author,
            real=False,
        )
        await self.process_tag(ctx, tag)
        await ctx.tick()

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if (
            message.author.bot
            or not isinstance(message.author, discord.Member)
            or not message.guild
        ):
            return
        if not self.guild_tag_cache[message.guild.id]:
            return
        if not await self.bot.message_eligible_as_command(message):
            return
        ctx = await self.bot.get_context(message)
        if ctx.prefix is None:
            return

        tag_command = message.content[len(ctx.prefix) :]
        tag_split = tag_command.split(" ", 1)
        if self.get_tag(message.guild, tag_split[0]):
            new_message = copy(message)
            new_message.content = f"{ctx.prefix}tag False {tag_command}"
            ctx = await self.bot.get_context(new_message)
            await self.bot.invoke(ctx)

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
        await tag.update_config()
        to_gather = []
        command_messages = []
        content = output.body[:2000] if output.body else None
        actions = output.actions
        embed = actions.get("embed")
        destination = ctx.channel
        replying = False

        if actions:
            if actions.get("requires") or actions.get("blacklist"):
                check, response = await self.validate_checks(ctx, actions)
                if check is False:
                    if response is not None:
                        if response:
                            await ctx.send(response[:2000])
                    else:
                        start_adding_reactions(ctx.message, ["❌"])
                    return
            if delete := actions.get("delete"):
                if ctx.channel.permissions_for(ctx.me).manage_messages:
                    to_gather.append(delete_quietly(ctx.message))
            if not delete and (reactu := actions.get("reactu")):
                to_gather.append(self.do_reactu(ctx, reactu))
            if actions.get("commands"):
                for command in actions["commands"]:
                    if command.startswith("tag"):
                        await ctx.send("Looping isn't allowed.")
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
        if content or embed:
            msg = await self.send_tag_response(ctx, destination, replying, content, embed=embed)
            if msg and (react := actions.get("react")):
                to_gather.append(self.do_reactions(ctx, react, msg))
        if command_messages:
            silent = actions.get("silent", False)
            overrides = actions.get("overrides")
            to_gather.append(
                asyncio.gather(
                    *[
                        self.process_command(message, silent, overrides)
                        for message in command_messages
                    ]
                )
            )

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

    async def process_command(
        self, command_message: discord.Message, silent: bool, overrides: dict
    ):
        ctx = await self.bot.get_context(
            command_message, cls=SilentContext if silent is True else commands.Context
        )
        if ctx.valid:
            if overrides:
                command = copy(ctx.command)
                # command = commands.Command()
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

    async def validate_checks(self, ctx: commands.Context, actions: dict) -> Tuple[bool, str]:
        role_ids = [r.id for r in ctx.author.roles]
        channel_id = ctx.channel.id
        if requires := actions.get("requires"):
            for argument in requires["items"]:
                role_or_channel = await self.role_or_channel_convert(ctx, argument)
                if role_or_channel:
                    if isinstance(role_or_channel, discord.Role):
                        if role_or_channel.id not in role_ids:
                            return False, requires["response"]
                    else:
                        if role_or_channel.id != channel_id:
                            return False, requires["response"]
        if blacklist := actions.get("blacklist"):
            for argument in blacklist["items"]:
                role_or_channel = await self.role_or_channel_convert(ctx, argument)
                if role_or_channel:
                    if isinstance(role_or_channel, discord.Role):
                        if role_or_channel.id in role_ids:
                            return False, blacklist["response"]
                    else:
                        if role_or_channel.id == channel_id:
                            return False, blacklist["response"]
        return True, ""

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
