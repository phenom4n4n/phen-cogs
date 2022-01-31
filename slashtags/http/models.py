"""
MIT License

Copyright (c) 2020-present phenom4n4n

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

import asyncio
import logging
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Tuple, Union

import discord

if TYPE_CHECKING:
    from .httpclient import SlashHTTP

log = logging.getLogger("red.phenom4n4n.slashtags.models")

__all__ = (
    "SlashOptionType",
    "ButtonStyle",
    "InteractionCallbackType",
    "ApplicationCommandType",
    "ApplicationOptionChoice",
    "ResponseOption",
    "Component",
    "Button",
    "InteractionMessage",
    "UnknownCommand",
    "InteractionType",
    "InteractionResponse",
    "InteractionButton",
    "InteractionCommand",
    "InteractionAutocomplete",
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
    | Choices | Offers a list of choices for the user to pick.                                                        | ``{choice}``         | :doc:`StringAdapter <tse:adapter>`         |
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


class ButtonStyle(IntEnum):
    blurple = 1
    grey = 2
    green = 3
    red = 4
    link = 5


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


# {'options': [{'value': 'args', 'type': 3, 'name': 'args'}]
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


class Component:
    __slots__ = ("type", "components", "style", "label", "custom_id", "url", "emoji", "disabled")

    def __init__(
        self,
        type: int = 1,
        *,
        components: List["Component"] = None,
        style: ButtonStyle = None,
        label: str = None,
        custom_id: int = None,
        url: str = None,
        emoji: Union[discord.PartialEmoji, str] = None,
        disabled: bool = False,
    ):
        self.type = type
        self.components = components or []
        self.style = style
        self.label = label
        self.custom_id = str(custom_id) if custom_id else None
        self.url = url
        self.emoji = emoji
        if emoji and isinstance(emoji, str):
            self.emoji = discord.PartialEmoji(name=emoji)
        self.disabled = disabled

    def __repr__(self):
        kwargs = " ".join(
            f"{k}={v!r}" for k, v in self.get_slotted_items() if v and not k.startswith("_")
        )
        return f"<{type(self).__name__} {kwargs}>"

    def to_dict(self):
        data = {"type": self.type}
        if self.type == 1:
            data["components"] = [c.to_dict() for c in self.components]
        else:  # elif type == 2:
            data["style"] = self.style.value
            if self.label:
                data["label"] = self.label
            if self.custom_id:
                data["custom_id"] = self.custom_id
            if self.url:
                data["url"] = self.url
            if self.emoji:
                data["emoji"] = self.emoji.to_dict()
            if self.disabled:
                data["disabled"] = self.disabled
        return data

    @classmethod
    def from_dict(cls, data: dict):
        type = data.pop["type"]
        components = [cls.from_dict(c) for c in data.get("components", [])]
        style = ButtonStyle(data.get("style"), 1)
        label = data.get("label")
        custom_id = data.get("custom_id")
        url = data.get("url")
        return cls(
            type, components=components, style=style, label=label, custom_id=custom_id, url=url
        )

    def get_slotted_items(self) -> Iterator[Tuple[str, Any]]:
        for slot in self.__slots__:
            yield slot, getattr(self, slot)


class Button(Component):
    def __init__(self, **kwargs):
        super().__init__(2, **kwargs)


class InteractionMessage(discord.Message):
    def __init__(
        self,
        interaction,
        *,
        state: discord.state.AutoShardedConnectionState,
        channel: discord.TextChannel,
        data: dict,
    ):
        super().__init__(state=state, channel=channel, data=data)
        self.interaction = interaction
        self.http = interaction.http
        self._token = interaction._token

    async def edit(
        self,
        *,
        content: str = None,
        embed: discord.Embed = None,
        embeds: List[discord.Embed] = None,
        allowed_mentions: discord.AllowedMentions = None,
    ):
        return await self.http.edit_message(
            self._token,
            self.id,
            content=content,
            embed=embed,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
        )

    async def delete(self, *, delay=None):
        if delay is not None:

            async def delete():
                await asyncio.sleep(delay)
                try:
                    await self.http.delete_message(self._token, self.id)
                except discord.HTTPException:
                    pass

            asyncio.create_task(delete())
        else:
            await self.http.delete_message(self._token, self.id)

    @property
    def reply(self):
        return self.interaction.send


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


class InteractionType(IntEnum):
    UNKNOWN = -1
    APPLICATION_COMMAND = 2
    MESSAGE_COMPONENT = 3
    APPLICATION_COMMAND_AUTOCOMPLETE = 4

    @classmethod
    def _missing_(cls):
        return cls.UNKNOWN


class InteractionResponse:
    __slots__ = (
        "cog",
        "bot",
        "http",
        "_state",
        "id",
        "type",
        "version",
        "_token",
        "_original_data",
        "guild_id",
        "channel_id",
        "_channel",
        "application_id",
        "author_id",
        "author",
        "interaction_data",
        "sent",
        "deferred",
        "completed",
        "options",
    )

    def __init__(self, *, cog, data: dict):
        self.cog = cog
        self.bot = cog.bot
        self.http: SlashHTTP = cog.http
        self._state: discord.state.AutoShardedConnectionState = self.bot._connection
        self.id = int(data["id"])
        self.type = InteractionType(data["type"])
        self.version = data["version"]
        self._token = data["token"]
        self._original_data = data

        self.guild_id = guild_id = discord.utils._get_as_snowflake(data, "guild_id")
        self.channel_id = discord.utils._get_as_snowflake(data, "channel_id")
        self._channel = None
        self.application_id = discord.utils._get_as_snowflake(data, "application_id")

        self.options: List[ResponseOption] = []

        if guild_id:
            member_data = data["member"]
            self.author_id = int(member_data["user"]["id"])
            self.author = discord.Member(data=member_data, state=self._state, guild=self.guild)
        else:
            member_data = data["user"]
            self.author_id = int(member_data["id"])
            self.author = discord.User(data=member_data, state=self._state)

        self.interaction_data = data["data"]
        self.sent = False
        self.deferred = False
        self.completed = False

    def __repr__(self):
        return (
            f"<{type(self).__name__} id={self.id} channel={self.channel!r} author={self.author!r}>"
        )

    @classmethod
    def from_interaction(cls, *, cog, data: dict):
        interaction_type = InteractionType(data["type"])
        classes = {
            InteractionType.APPLICATION_COMMAND: InteractionCommand,
            InteractionType.MESSAGE_COMPONENT: InteractionButton,
            InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE: InteractionAutocomplete,
        }
        cls = classes.get(interaction_type, cls)
        return cls(cog=cog, data=data)

    @property
    def guild(self) -> discord.Guild:
        return self.bot.get_guild(self.guild_id)

    @property
    def channel(self) -> discord.TextChannel:
        if channel := self._channel:
            return channel
        elif self.guild_id:
            if guild_channel := self.guild.get_channel(self.channel_id):
                self._channel = channel
                return guild_channel
        elif dm_channel := self.bot.get_channel(self.channel_id):
            self._channel = dm_channel
            return dm_channel

    async def get_channel(self) -> Union[discord.TextChannel, discord.DMChannel]:
        if channel := self.channel:
            return channel
        if not self.guild_id:
            self._channel = await self.author.create_dm()
        else:
            self._channel = await self.bot.fetch_channel(self.channel_id)
        return self._channel

    @property
    def created_at(self):
        return discord.utils.snowflake_time(self.id)

    async def send(
        self,
        content: str = None,
        *,
        file: discord.File = None,
        files: List[discord.File] = None,
        embed: discord.Embed = None,
        embeds: List[discord.Embed] = None,
        tts: bool = False,
        allowed_mentions: discord.AllowedMentions = None,
        hidden: bool = False,
        delete_after: int = None,
        reference=None,  # this parameter and the one below are unused
        mention_author=None,  # they exist to prevent replies from erroring
    ):
        flags = 64 if hidden else None
        initial = not self.sent
        data = await self.http.send_message(
            self._token,
            self.id,
            type=InteractionCallbackType.channel_message_with_source,
            initial_response=initial,
            content=content,
            file=file,
            files=files,
            embed=embed,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            tts=tts,
            flags=flags,
        )

        if initial:
            self.sent = True
        if not self.completed:
            self.completed = True

        if data:
            try:
                message = InteractionMessage(
                    self,
                    data=data,
                    channel=self.channel,
                    state=self._state,
                )
            except Exception as e:
                log.exception("Failed to create message object for data:\n%r", data, exc_info=e)
            else:
                if delete_after is not None:
                    await message.delete(delay=delete_after)
                return message

    reply = send

    async def defer(self, *, hidden: bool = False):
        flags = 64 if hidden else None
        initial = not self.sent
        data = await self.http.send_message(
            self._token,
            self.id,
            type=InteractionCallbackType.deferred_channel_message_with_source,
            initial_response=initial,
            flags=flags,
        )
        if not self.sent:
            self.sent = True
        self.deferred = True
        return data

    def _parse_options(self):
        options = self.interaction_data.get("options", [])
        resolved = self.interaction_data.get("resolved", {})
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
            if channel := self.guild.get_channel(channel_id):
                pass
            else:
                channel = discord.TextChannel(
                    state=self._state, guild=self.guild, data=resolved_channel
                )
        else:
            if channel := self._state._get_private_channel(channel_id):
                pass
            else:
                channel = discord.DMChannel(
                    state=self._state, me=self.bot.user, data=resolved_channel
                )
        option.set_value(channel)
        return option

    def _handle_option_user(
        self, data: dict, option: ResponseOption, resolved: Dict[str, Dict[str, dict]]
    ):
        user_id = int(data["value"])
        resolved_user = resolved["users"][data["value"]]
        if self.guild_id:
            if user := self.guild.get_member(user_id):
                pass
            else:
                user = discord.Member(guild=self.guild, data=resolved_user, state=self._state)
                self.guild._add_member(user)
        else:
            user = self._state.store_user(resolved_user)
        option.set_value(user)
        return option

    def _handle_option_role(
        self, data: dict, option: ResponseOption, resolved: Dict[str, Dict[str, dict]]
    ):
        role_id = int(data["value"])
        resolved_role = resolved["roles"][data["value"]]
        if self.guild_id:
            if role := self.guild.get_role(role_id):
                pass
            else:
                role = discord.Role(guild=self.guild, data=resolved_role, state=self)
                self.guild._add_role(role)
            option.set_value(role)
        return option


class InteractionButton(InteractionResponse):
    __slots__ = ("custom_id", "component_type", "message")

    def __init__(self, *, cog, data: dict):
        super().__init__(cog=cog, data=data)
        interaction_data = self.interaction_data
        self.custom_id = interaction_data["custom_id"]
        self.component_type = interaction_data["component_type"]

        message = data["message"]
        if reference := message.get("message_reference"):
            if "channel_id" not in reference:
                reference["channel_id"] = self.channel_id
                # used if dislash is loaded since Message.reference creation
                # pops channel_id from the message_reference dict

        try:
            self.message = discord.Message(channel=self.channel, data=message, state=self._state)
        except Exception as exc:
            log.exception("An error occured while creating the message for %r", self, exc_info=exc)
            self.message = None

    async def defer_update(self, *, hidden: bool = False):
        flags = 64 if hidden else None
        initial = not self.sent
        data = await self.http.send_message(
            self._token,
            self.id,
            type=InteractionCallbackType.deferred_update_message,
            initial_response=initial,
            flags=flags,
        )
        if not self.sent:
            self.sent = True
        self.deferred = True
        return data

    async def update(
        self,
        content: str = None,
        *,
        embed: discord.Embed = None,
        embeds: List[discord.Embed] = None,
        tts: bool = False,
        allowed_mentions: discord.AllowedMentions = None,
        hidden: bool = False,
        delete_after: int = None,
        components: List[Component] = None,
    ):
        flags = 64 if hidden else None
        initial = not self.sent
        if initial:
            data = await self.http.send_message(
                self._token,
                self.id,
                type=InteractionCallbackType.update_message,
                initial_response=initial,
                content=content,
                embed=embed,
                embeds=embeds,
                allowed_mentions=allowed_mentions,
                tts=tts,
                flags=flags,
                components=components,
            )
            self.sent = True
        else:
            data = await self.http.edit_message(
                self._token,
                content=content,
                embed=embed,
                embeds=embeds,
                allowed_mentions=allowed_mentions,
                components=components,
                original=True,
            )

        if not self.completed:
            self.completed = True


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

    def __init__(self, parent: "InteractionCommand"):
        self._data = parent.interaction_data.get("resolved", {})
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


class InteractionCommand(InteractionResponse):
    __slots__ = (
        "command_type",
        "command_name",
        "command_id",
        "_cs_content",
        "target_id",
        "resolved",
    )

    def __init__(self, *, cog, data: dict):
        super().__init__(cog=cog, data=data)
        interaction_data = self.interaction_data
        self.command_type = ApplicationCommandType(interaction_data["type"])
        self.command_name = interaction_data["name"]
        self.command_id = int(interaction_data["id"])
        self.target_id: Optional[int] = discord.utils._get_as_snowflake(
            interaction_data, "target_id"
        )
        self.resolved: InteractionResolved = InteractionResolved(self)
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
    def command(self):
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


class InteractionAutocomplete(InteractionResponse):
    def __init__(self, *, cog, data: dict):
        super().__init__(cog=cog, data=data)
        self._parse_options()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} options={self.options!r}>"

    async def send_autocomplete_choices(self, choices: List[ApplicationOptionChoice]):
        await self.http.autocomplete(
            self._token, self.id, [choice.to_dict() for choice in choices]
        )
