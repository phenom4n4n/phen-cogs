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
from typing import Coroutine, List, Optional

import aiohttp
import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import humanize_list
from TagScriptEngine import __version__ as tse_version

from .abc import CompositeMetaClass
from .commands import Commands
from .errors import MissingTagPermissions, TagCharacterLimitReached
from .objects import Tag
from .owner import OwnerCommands
from .processor import Processor

log = logging.getLogger("red.phenom4n4n.tags")

TAGSCRIPT_LIMIT = 10_000


class Tags(
    Commands,
    OwnerCommands,
    Processor,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    """
    Create and use tags.

    The TagScript documentation can be found [here](https://phen-cogs.readthedocs.io/en/latest/).
    """

    __version__ = "2.3.4"
    __author__ = ("PhenoM4n4n",)

    def format_help_for_context(self, ctx: commands.Context):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        text = [
            f"{pre_processed}{n}",
            f"Cog Version: **{self.__version__}**",
            f"TagScriptEngine Version: **{tse_version}**",
            f"Author: {humanize_list(self.__author__)}",
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
        default_global = {"tags": {}, "blocks": {}, "async_enabled": False, "dot_parameter": False}
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)

        self.guild_tag_cache = defaultdict(dict)
        self.global_tag_cache = {}
        self.initialize_task = None
        self.dot_parameter: bool = None
        self.async_enabled: bool = None
        # self.initialize_task = self.create_task(self.initialize())

        self.session = aiohttp.ClientSession()
        self.docs: list = []

        bot.add_dev_env_value("tags", lambda ctx: self)
        super().__init__()

    def cog_unload(self):
        try:
            self.__unload()
        except Exception as e:
            log.exception("An error occurred during cog unload.", exc_info=e)

    def __unload(self):
        self.bot.remove_dev_env_value("tags")
        if self.initialize_task:
            self.initialize_task.cancel()
        asyncio.create_task(self.session.close())
        super().cog_unload()

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

    def task_done_callback(self, task: asyncio.Task):
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as error:
            log.exception(f"Task failed.", exc_info=error)

    def create_task(self, coroutine: Coroutine, *, name: str = None):
        task = asyncio.create_task(coroutine, name=name)
        task.add_done_callback(self.task_done_callback)
        return task

    async def initialize(self):
        data = await self.config.all()
        await self.initialize_interpreter(data)

        global_tags = data["tags"]
        async for global_tag_name, global_tag_data in AsyncIter(global_tags.items(), steps=50):
            tag = Tag.from_dict(self, global_tag_name, global_tag_data)
            tag.add_to_cache()

        guilds_data = await self.config.all_guilds()
        async for guild_id, guild_data in AsyncIter(guilds_data.items(), steps=100):
            await self.cache_guild(guild_id, guild_data)

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

    def get_unique_tags(self, guild: Optional[discord.Guild] = None) -> List[Tag]:
        path = self.guild_tag_cache[guild.id] if guild else self.global_tag_cache
        return sorted(set(path.values()), key=lambda t: t.name)

    async def validate_tagscript(self, ctx: commands.Context, tagscript: str):
        length = len(tagscript)
        if length > TAGSCRIPT_LIMIT:
            raise TagCharacterLimitReached(TAGSCRIPT_LIMIT, length)
        output = self.engine.process(tagscript)
        if self.async_enabled:
            output = await output
        is_owner = await self.bot.is_owner(ctx.author)
        if is_owner:
            return True
        author_perms = ctx.channel.permissions_for(ctx.author)
        if output.actions.get("overrides") and not author_perms.manage_guild:
            raise MissingTagPermissions(
                "You must have **Manage Server** permissions to use the `override` block."
            )
        if output.actions.get("allowed_mentions") and not is_owner:
            raise MissingTagPermissions(
                "You must have **Mention Everyone** permissions to use the `allowedmentions` block."
            )
        return True
