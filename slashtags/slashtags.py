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
from typing import Coroutine, Dict

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

from .abc import CompositeMetaClass
from .blocks import HideBlock
from .commands import Commands
from .http import SlashHTTP
from .models import InteractionResponse, SlashOptionType
from .objects import (CommandModel, FakeMessage, SlashContext, SlashOption,
                      SlashTag)
from .processor import Processor
from .utils import dev_check

log = logging.getLogger("red.phenom4n4n.slashtags")


class SlashTags(Commands, Processor, commands.Cog, metaclass=CompositeMetaClass):
    """
    Create custom slash commands.

    The TagScript documentation can be found [here](https://phen-cogs.readthedocs.io/en/latest/index.html).
    """

    __version__ = "0.2.0"
    __author__ = ["PhenoM4n4n"]

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
                await self.set_app_id()

    async def initialize_task(self):
        await self.cache_tags()
        if self.application_id is None:
            if self.bot.user is None:
                await self.bot.wait_until_ready()
            await self.set_app_id()

    async def set_app_id(self):
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

    @commands.Cog.listener()
    async def on_interaction_create(self, data: dict):
        log.debug("Interaction data received:\n%s" % data)
        handlers = {2: self.handle_slash_interaction, 3: self.handle_slash_button}
        handler = handlers.get(data["type"], self.handle_slash_interaction)
        try:
            await handler(data)
        except Exception as e:
            log.exception(
                "An exception occured while handling an interaction:\n%s" % data, exc_info=e
            )

    async def handle_slash_button(self, button):
        ...

    async def handle_slash_interaction(self, data: dict):
        interaction = InteractionResponse(data=data, cog=self)
        self.bot.dispatch("slash_interaction", interaction)

    @commands.Cog.listener()
    async def on_slash_interaction(self, interaction: InteractionResponse):
        try:
            command = interaction.command
            if isinstance(command, CommandModel):
                tag = self.get_tag(interaction.guild, command.id)
                await self.process_tag(interaction, tag)
            elif interaction.command_id == self.eval_command:
                await self.slash_eval(interaction)
            else:
                log.debug("Unknown interaction created:\n%r" % interaction)
        except Exception as e:
            ctx = SlashContext.from_interaction(interaction)
            self.bot.dispatch("command_error", ctx, commands.CommandInvokeError(e))
