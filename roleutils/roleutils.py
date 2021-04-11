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

# Multi-file class combining taken from https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/mod/mod.py
import logging
from abc import ABC
from typing import Literal

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

from .autorole import AutoRole
from .reactroles import ReactRoles
from .roles import Roles

log = logging.getLogger("red.phenom4n4n.roleutils")

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """


class RoleUtils(
    Roles,
    ReactRoles,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    """
    Useful role commands.

    Includes massroling, role targeting, and reaction roles.
    """

    __version__ = "1.3.5"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\nCog Version: {self.__version__}"

    def __init__(self, bot: Red, *_args) -> None:
        self.cache = {}
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=326235423452394523,
            force_registration=True,
        )
        default_guild = {"reactroles": {"channels": [], "enabled": True}}
        self.config.register_guild(**default_guild)

        default_guildmessage = {"reactroles": {"react_to_roleid": {}}}
        self.config.init_custom("GuildMessage", 2)
        self.config.register_custom("GuildMessage", **default_guildmessage)
        super().__init__(*_args)

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        return

    async def initialize(self):
        log.debug("RoleUtils initialize")
        await super().initialize()
