# Multi-file class combining taken from https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/mod/mod.py
import asyncio
import logging
import re
from abc import ABC
from typing import List, Tuple, Literal
import discord

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

from .roles import Roles
from .reactroles import ReactRoles

log = logging.getLogger("red.phenom4n4n.roleutils")

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """

    pass


class RoleUtils(
    Roles,
    ReactRoles,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    """
    Useful role commands.
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=326235423452394523,
            force_registration=True,
        )
        default_guild = {
            "reactroles": {}
        }
        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        return
