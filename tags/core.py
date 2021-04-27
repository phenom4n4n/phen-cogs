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
from typing import Optional, Set

import aiohttp
import discord
import TagScriptEngine as tse
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import PrivilegeLevel, Requires
from redbot.core.config import Config
from redbot.core.utils import AsyncIter
from redbot.core.utils.menus import (DEFAULT_CONTROLS, close_menu, menu,
                                     start_adding_reactions)
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate

from .abc import CompositeMetaClass
from .blocks import (DeleteBlock, ReactBlock, ReactUBlock, RedirectBlock,
                     SilentBlock)
from .commands import Commands
from .errors import MissingTagPermissions, TagFeedbackError
from .objects import SilentContext, Tag
from .processor import Processor

log = logging.getLogger("red.phenom4n4n.tags")


class Tags(
    Commands,
    Processor,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    """
    Create and use tags.

    The TagScript documentation can be found [here](https://phen-cogs.readthedocs.io/en/latest/).
    """

    __version__ = "2.2.1"

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
        self.cache_task = asyncio.create_task(self.cache_tags())

        self.session = aiohttp.ClientSession()
        self.docs: list = []

        super().__init__()
        bot.add_dev_env_value("tags", lambda ctx: self)
        bot.add_dev_env_value("tse", lambda ctx: tse)

    def cog_unload(self):
        self.bot.remove_dev_env_value("tags")
        self.bot.remove_dev_env_value("tse")
        if self.cache_task:
            self.cache_task.cancel()
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
            await self.cache_guild(guild_id, guild_data)

        global_tags = await self.config.tags()
        async for global_tag_name, global_tag_data in AsyncIter(global_tags.items(), steps=50):
            tag = Tag.from_dict(self, global_tag_name, global_tag_data)
            tag.add_to_cache()

        log.debug("Built tag cache.")

    async def cache_guild(self, guild_id: int, guild_data: dict):
        async for tag_name, tag_data in AsyncIter(guild_data["tags"].items(), steps=50):
            tag = Tag.from_dict(self, tag_name, tag_data, guild_id=guild_id)
            tag.add_to_cache()

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

    def get_unique_tags(self, guild: Optional[discord.Guild] = None) -> Set[Tag]:
        path = self.guild_tag_cache[guild.id] if guild else self.global_tag_cache
        return set(path.values())

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

    async def cog_command_error(self, ctx: commands.Context, exc: Exception):
        if isinstance(exc, commands.CommandInvokeError):
            error = exc.original
            if isinstance(error, TagFeedbackError):
                try:
                    await ctx.reply(error)
                except discord.HTTPException:
                    await ctx.send(error)
            else:
                await self.bot.on_command_error(ctx, exc, unhandled_by_cog=True)
        else:
            await self.bot.on_command_error(ctx, exc, unhandled_by_cog=True)
