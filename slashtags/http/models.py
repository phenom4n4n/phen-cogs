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

from __future__ import annotations

import logging
from datetime import datetime
from enum import IntEnum
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import discord

if TYPE_CHECKING:
    from ..objects import ApplicationCommand
    from .httpclient import SlashHTTP

log = logging.getLogger("red.phenom4n4n.slashtags.models")

__all__ = (
    "SlashOptionType",
    "InteractionCallbackType",
    "ApplicationCommandType",
    "ApplicationOptionChoice",
    "ResponseOption",
    "UnknownCommand",
    "InteractionWrapper",
    "InteractionCommandWrapper",
    "InteractionAutocompleteWrapper",
)


class SlashOptionType(IntEnum):
    """
    +---------+-------------------------------------------------------------------------------------------------------+----------------------+--------------------------------------------+
    | Type    | Description                                                                                           | Example              | Adapter                                    |
    +=========+=======================================================================================================+======================+============================================+
    | String  | Accepts any user inputted text as an argument.                                                        | ``{string}``         | :doc:`StringAdapter <tse:adapter>`         |
    +---------+-------------------------------------------------------------------------------------------------------+----------------------+--------------------------------------------+
    | Integer | Only allows integer input for the argument.                                                           | ``{integer}``        | :doc:`IntAdapter <tse:adapter>`            |
    +---------+-------------------------------------------------------------------------------------------------------+----------------------+--------------------------------------------+
    | Boolean | Allows either ``True`` or ``False`` as input.                                                         | ``{boolean}``        | :doc:`StringAdapter <tse:adapter>`         |
    +---------+-------------------------------------------------------------------------------------------------------+----------------------+--------------------------------------------+
    | User    | Refers to a member of the server or a member in the DM channel, accepting username or IDs as input.   | ``{user(name)}``     | :doc:`MemberAdapter <tse:adapter>`         |
    +---------+-------------------------------------------------------------------------------------------------------+----------------------+--------------------------------------------+
    | Channel | Refers to a text, voice, or category channel in this server, accepting channel names or IDs as input. | ``{channel(topic)}`` | :doc:`ChannelAdapter <tse:adapter>`        |
    +---------+-------------------------------------------------------------------------------------------------------+----------------------+--------------------------------------------+
    | Role    | Refers to a server role, accepting role name or IDs as input.                                         | ``{role(id)}``       | :doc:`SafeObjectAdapter <tse:adapter>`     |
    +---------+-------------------------------------------------------------------------------------------------------+----------------------+--------------------------------------------+
    | Number  | Accepts any floating point number.                                                                    | ``{number}``         | :doc:`StringAdapter <tse:adapter>`         |
    +---------+-------------------------------------------------------------------------------------------------------+----------------------+--------------------------------------------+
    | Choices | Offers a list of string choices for the user to pick.                                                 | ``{choice}``         | :doc:`StringAdapter <tse:adapter>`         |
    |         | Each option has a name and underlying value which is returned as string argument when accessed.       |                      |                                            |
    +---------+-------------------------------------------------------------------------------------------------------+----------------------+--------------------------------------------+
    """

    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8
    NUMBER = 10

    CHOICES = -1
    # doesn't exist as a seperate value in the API, but is used for the choices option

    @classmethod
    def get_descriptions(cls) -> Dict[SlashOptionType, str]:
        return {
            cls.STRING: "Accepts any user inputted text as an argument.",
            cls.INTEGER: "Only allows integer input for the argument.",
            cls.BOOLEAN: "Allows either `True` or `False` as input.",
            cls.USER: "Refers to a member of the server, accepting username or IDs as input.",
            cls.CHANNEL: "Refers to a text, voice, or category channel in this server.",
            cls.ROLE: "Refers to a server role, accepting role name or IDs as input.",
            cls.NUMBER: "Accepts any floating point number.",
            cls.CHOICES: "Offers a list of string choices for the user to pick.",
        }

    @property
    def description(self) -> str:
        return self.get_descriptions()[self]


class InteractionCallbackType(IntEnum):
    pong = 1
    channel_message_with_source = 4
    deferred_channel_message_with_source = 5
    deferred_update_message = 6
    update_message = 7
    application_command_autocomplete_result = 8


class ApplicationCommandType(IntEnum):
    CHAT_INPUT = 1
    USER = 2
    MESSAGE = 3

    def get_human_name(self) -> str:
        humanized_types = {
            self.CHAT_INPUT: "slash",
            self.USER: "user",
            self.MESSAGE: "message",
        }
        return humanized_types.get(self, "unknown")

    def get_prefix(self) -> str:
        command_prefixes = {
            self.CHAT_INPUT: "/",
            self.MESSAGE: "[message] ",
            self.USER: "[user] ",
        }
        return command_prefixes.get(self, "/")


class ApplicationOptionChoice:
    __slots__ = ("name", "value")

    def __init__(self, name: str, value: Union[str, int]):
        self.name = name
        self.value = value

    def to_dict(self):
        return {"name": self.name, "value": self.value}

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data["name"], data["value"])


class ResponseOption:
    __slots__ = ("type", "name", "value", "focused")

    def __init__(self, *, type: SlashOptionType, name: str, value: str, focused: bool = False):
        self.type = type
        self.name = name
        self.value = value
        self.focused = focused

    def set_value(self, value):
        self.value = value

    def __repr__(self):
        members = ("type", "name", "value", "focused")
        attrs = " ".join(f"{member}={getattr(self, member)!r}" for member in members)
        return f"<{self.__class__.__name__} {attrs}>"

    @classmethod
    def from_dict(cls, data: dict):
        type = SlashOptionType(data.get("type", 3))
        return cls(
            type=type, name=data["name"], value=data["value"], focused=data.get("focused", False)
        )


class UnknownCommand:
    __slots__ = ("id",)
    cog = None

    def __init__(self, *, id: int = None):
        self.id = id

    def __repr__(self) -> str:
        return f"UnknownCommand(id={self.id})"

    @property
    def name(self):
        return self.__repr__()

    @property
    def qualified_name(self):
        return self.__repr__()

    def __bool__(self) -> bool:
        return False


class InteractionWrapper:
    __slots__ = (
        "interaction",
        "cog",
        "http",
        "bot",
        "options",
        "completed",
        "_channel",
    )
    PROXIED_ATTRIBUTES = {
        "_state",
        "id",
        "type",
        "version",
        "token",
        "data",
        "channel_id",
        "channel",
        "guild",
        "guild_id",
        "application_id",
        "user",
        "permissions",
        "response",
        "followup",
    }

    def __init__(self, interaction: discord.Interaction, cog):
        self.interaction = interaction
        self.cog = cog
        self.http: SlashHTTP = cog.http
        self.bot = cog.bot
        self.options = []
        self.completed = False
        self._channel: Optional[discord.TextChannel | discord.PartialMessageable] = None

    def __dir__(self) -> List[str]:
        default = super().__dir__()
        default.extend(self.PROXIED_ATTRIBUTES)
        return default

    def __getattr__(self, name: str):
        if name in self.PROXIED_ATTRIBUTES:
            return getattr(self.interaction, name)
        raise AttributeError(f"{self.__class__.__name__!r} object has no attribute {name!r}")

    @property
    def created_at(self) -> datetime:
        return discord.utils.snowflake_time(self.id)

    @property
    def author(self) -> discord.User | discord.Member:
        return self.interaction.user

    async def get_channel(self) -> discord.TextChannel | discord.PartialMessageable:
        if isinstance(self.interaction, discord.PartialMessageable):
            self._channel = self.author.dm_channel or await self.author.create_dm()
        else:
            self._channel = self.interaction.channel
        return self._channel

    def send(self, *args, **kwargs):
        to_pop = ("reference", "mention_author")
        for name in to_pop:
            kwargs.pop(name, None)
        response = self.interaction.response
        method = self.interaction.followup.send if response.is_done() else response.send_message
        self.completed = True
        return method(*args, **kwargs)

    def _parse_options(self):
        data = self.interaction.data
        options = data.get("options", [])
        resolved = data.get("resolved", {})
        for o in options:
            option = ResponseOption.from_dict(o)
            handler_name = f"_handle_option_{option.type.name.lower()}"
            try:
                handler = getattr(self, handler_name)
            except AttributeError:
                pass
            else:
                try:
                    option = handler(o, option, resolved)
                except Exception as error:
                    log.exception(
                        "Failed to handle option data for option:\n%r", o, exc_info=error
                    )
            self.options.append(option)

    def _handle_option_channel(
        self, data: dict, option: ResponseOption, resolved: Dict[str, Dict[str, dict]]
    ):
        channel_id = int(data["value"])
        resolved_channel = resolved["channels"][data["value"]]
        if self.guild_id:
            if not (channel := self.guild.get_channel(channel_id)):
                channel = discord.TextChannel(
                    state=self._state, guild=self.guild, data=resolved_channel
                )
        elif not (channel := self._state._get_private_channel(channel_id)):
            channel = discord.DMChannel(state=self._state, me=self.bot.user, data=resolved_channel)
        option.set_value(channel)
        return option

    def _handle_option_user(
        self, data: dict, option: ResponseOption, resolved: Dict[str, Dict[str, dict]]
    ):
        resolved_user = resolved["users"][data["value"]]
        if self.guild_id:
            user_id = int(data["value"])
            if not (user := self.guild.get_member(user_id)):
                user = discord.Member(guild=self.guild, data=resolved_user, state=self._state)
                self.guild._add_member(user)
        else:
            user = self._state.store_user(resolved_user)
        option.set_value(user)
        return option

    def _handle_option_role(
        self, data: dict, option: ResponseOption, resolved: Dict[str, Dict[str, dict]]
    ):
        resolved_role = resolved["roles"][data["value"]]
        if self.guild_id:
            role_id = int(data["value"])
            if not (role := self.guild.get_role(role_id)):
                role = discord.Role(guild=self.guild, data=resolved_role, state=self)
                self.guild._add_role(role)
            option.set_value(role)
        return option


class InteractionCommandWrapper(InteractionWrapper):
    __slots__ = (
        "command_type",
        "command_name",
        "command_id",
        "_cs_content",
        "target_id",
        "resolved",
    )

    def __init__(self, interaction: discord.Interaction, cog):
        super().__init__(interaction, cog)
        interaction_data = self.data
        self.command_type = ApplicationCommandType(interaction_data["type"])
        self.command_name = interaction_data["name"]
        self.command_id = int(interaction_data["id"])
        self.target_id: Optional[int] = discord.utils._get_as_snowflake(
            interaction_data, "target_id"
        )
        self.resolved: Optional[InteractionResolved] = InteractionResolved(self)
        self._parse_options()

    def __repr__(self) -> str:
        values = ("id", "command", "options", "channel", "author")
        inner = " ".join(f"{value}={getattr(self, value)!r}" for value in values)
        return f"<{type(self).__name__} {inner}"

    @discord.utils.cached_slot_property("_cs_content")
    def content(self):
        items = [f"/{self.command_name}"]
        for option in self.options:
            items.append(f"`{option.name}: {option.value}`")
        return " ".join(items)

    @property
    def command(self) -> ApplicationCommand | UnknownCommand:
        return self.cog.get_command(self.command_id) or UnknownCommand(id=self.command_id)

    @property
    def jump_url(self):
        guild_id = getattr(self.guild, "id", "@me")
        return f"https://discord.com/channels/{guild_id}/{self.channel_id}/{self.id}"

    def to_reference(self, *args, **kwargs):
        # return None to prevent reply since interaction responses already reply (visually)
        # additionally, replying to an interaction response raises
        # message_reference: Unknown message
        return

    @property
    def me(self):
        return self.guild.me if self.guild else self.bot.user


class InteractionResolved:
    __slots__ = (
        "_data",
        "_parent",
        "_state",
        "_users",
        "_members",
        "_roles",
        "_channels",
        "_messages",
    )

    def __init__(self, parent: InteractionCommandWrapper):
        self._data = parent.data.get("resolved", {})
        self._parent = parent
        self._state = parent._state
        self._users: Optional[Dict[int, discord.User]] = None
        self._members: Optional[Dict[int, discord.Member]] = None
        self._roles: Optional[Dict[int, discord.Role]] = None
        self._channels: Optional[Dict[int, Union[discord.TextChannel, discord.DMChannel]]] = None
        self._messages: Optional[Dict[int, discord.Message]] = None

    def __repr__(self) -> str:
        inner = " ".join(f"{k}={len(v)}" for k, v in self._data.items() if v)
        return f"<{type(self).__name__} {inner}>"

    @property
    def users(self) -> Dict[int, discord.User]:
        if self._users is not None:
            return self._users.copy()
        users = {
            int(user_id): self._state.store_user(user_data)
            for user_id, user_data in self._data.get("users", {}).items()
        }
        self._users = users
        return self.users

    @property
    def members(self) -> Dict[int, discord.Member]:
        ...

    @property
    def roles(self) -> Dict[int, discord.Role]:
        ...

    @property
    def channels(self) -> Dict[int, Union[discord.TextChannel, discord.DMChannel]]:
        ...

    @property
    def messages(self) -> Dict[int, discord.Message]:
        if self._messages is not None:
            return self._messages.copy()
        messages = {
            int(message_id): discord.Message(
                channel=self._parent.channel, data=message_data, state=self._state
            )
            for message_id, message_data in self._data.get("messages", {}).items()
        }
        self._messages = messages
        return self.messages


class InteractionAutocompleteWrapper(InteractionWrapper):
    def __init__(self, interaction: discord.Interaction, cog):
        super().__init__(interaction, cog)
        self._parse_options()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} options={self.options!r}>"

    async def send_autocomplete_choices(self, choices: List[ApplicationOptionChoice]):
        await self.http.autocomplete(
            self._token, self.id, [choice.to_dict() for choice in choices]
        )
