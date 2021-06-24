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
from functools import partial
from typing import Coroutine, Dict, Optional

import discord
import red_interactions as ri
import TagScriptEngine as tse
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import humanize_list

from .abc import CompositeMetaClass
from .mixins import Commands, Processor
from .objects import SlashContext, SlashTag

log = logging.getLogger("red.phenom4n4n.slashtags")


class SlashTags(Commands, Processor, commands.Cog, metaclass=CompositeMetaClass):
    """
    Create custom slash commands.

    The TagScript documentation can be found [here](https://phen-cogs.readthedocs.io/en/latest/index.html).
    """

    __version__ = "0.5.0"
    __author__ = ["PhenoM4n4n"]

    def format_help_for_context(self, ctx: commands.Context):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        text = [
            f"{pre_processed}{n}",
            f"Cog Version: **{self.__version__}**",
            f"TagScriptEngine Version: **{tse.__version__}**",
            f"Red-Interactions Version: **{ri.__version__}**",
            f"Author: {humanize_list(self.__author__)}",
        ]
        return "\n".join(text)

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.eval_command = None
        self.config = Config.get_conf(
            self,
            identifier=70342502093747959723475890,
            force_registration=True,
        )
        default_guild = {"tags": {}}
        default_global = {
            "eval_command": None,
            "tags": {},
            "testing_enabled": False,
        }
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)

        self.state: ri.InteractionState = None

        self.guild_tag_cache: Dict[int, Dict[int, SlashTag]] = defaultdict(dict)
        self.global_tag_cache: Dict[int, SlashTag] = {}

        self.load_task = self.create_task(self.initialize_task())
        bot.add_dev_env_value("st", lambda ctx: self)

        super().__init__()

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
        try:
            self.__unload()
        except Exception as error:
            log.exception("An error occurred while unloading the cog.", exc_info=error)

    def __unload(self):
        self.bot.remove_dev_env_value("st")
        if self.testing_enabled:
            self.remove_test_cog()
        self.load_task.cancel()

    async def cog_before_invoke(self, ctx: commands.Context) -> bool:
        if self.bot.get_cog("SlashInjector"):
            raise commands.UserFeedbackCheckFailure(
                "This cog no longer works with `slashinjector` by Kowlin/Sentinel.\n"
                f"Run `{ctx.clean_prefix}unload slashinjector`, then restart the bot to properly reinitialize the cog."
            )
        return True

    async def pre_load(self):
        self.state = await ri.initialize(self.bot) if not ri.is_initialized() else ri.state
        data = await self.config.all()
        self.eval_command = data["eval_command"]

        if data["testing_enabled"]:
            self.add_test_cog()
        await self.cache_tags(data)

    async def initialize_task(self):
        pass

    async def cache_tags(self, global_data: dict = None):
        guild_cached = 0
        guilds_data = await self.config.all_guilds()
        async for guild_id, guild_data in AsyncIter(guilds_data.items(), steps=100):
            for tag_data in guild_data["tags"].values():
                tag = SlashTag.from_dict(self, tag_data, guild_id=guild_id)
                tag.add_to_cache()
                guild_cached += 1

        cached = 0
        all_data = global_data or await self.config.all()
        for global_tag_data in all_data["tags"].values():
            tag = SlashTag.from_dict(self, global_tag_data)
            tag.add_to_cache()
            cached += 1

        log.debug(
            "completed caching slash tags, %s guild slash tags cached, %s global slash tags cached"
            % (guild_cached, cached)
        )

    async def validate_tagscript(self, ctx: commands.Context, tagscript: str):
        output = self.engine.process(tagscript)
        is_owner = await self.bot.is_owner(ctx.author)
        if is_owner:
            return True
        # TODO block validation
        ...
        return True

    def get_tag(
        self,
        guild: Optional[discord.Guild],
        tag_id: int,
        *,
        check_global: bool = True,
        global_priority: bool = False,
    ) -> Optional[SlashTag]:
        tag = None
        if global_priority and check_global:
            return self.global_tag_cache.get(tag_id)
        if guild is not None:
            tag = self.guild_tag_cache[guild.id].get(tag_id)
        if tag is None and check_global:
            tag = self.global_tag_cache.get(tag_id)
        return tag

    def get_tag_by_name(
        self,
        guild: Optional[discord.Guild],
        tag_name: str,
        *,
        check_global: bool = True,
        global_priority: bool = False,
    ) -> Optional[SlashTag]:
        tag = None
        get = partial(discord.utils.get, name=tag_name)
        if global_priority and check_global:
            return get(self.global_tag_cache.values())
        if guild is not None:
            tag = get(self.guild_tag_cache[guild.id].values())
        if tag is None and check_global:
            tag = get(self.global_tag_cache.values())
        return tag

    @commands.Cog.listener()
    async def on_red_slash_interaction(self, interaction: ri.InteractionCommand):
        try:
            await self.invoke_and_catch(interaction)
        except commands.CommandInvokeError as e:
            ctx = SlashContext.from_interaction(interaction)
            self.bot.dispatch("command_error", ctx, e)

    async def invoke_and_catch(self, interaction: ri.InteractionCommand):
        try:
            command = interaction.command
            if isinstance(command, ri.SlashCommand):
                tag = self.get_tag(interaction.guild, command.id)
                await self.process_tag(interaction, tag)
            elif interaction.command_id == self.eval_command:
                await self.slash_eval(interaction)
            else:
                log.debug("Unknown interaction created:\n%r" % interaction)
        except Exception as e:
            raise commands.CommandInvokeError(e) from e

    @property
    def testing_enabled(self):
        return bool(self.bot.get_cog("SlashTagTesting"))

    def add_test_cog(self):
        from .testing.test_cog import SlashTagTesting

        self.bot.add_cog(SlashTagTesting(self.bot))

    def remove_test_cog(self):
        self.bot.remove_cog("SlashTagTesting")
