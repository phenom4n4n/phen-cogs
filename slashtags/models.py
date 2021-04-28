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
import functools
import logging
from enum import IntEnum
from typing import Dict, List

import discord
from redbot.core.bot import Red

from .http import SlashHTTP

log = logging.getLogger("red.phenom4n4n.slashtags.models")


class SlashOptionType(IntEnum):
    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8


# {'options': [{'value': 'args', 'type': 3, 'name': 'args'}]
class ResponseOption:
    def __init__(self, *, type: SlashOptionType, name: str, value: str):
        self.type = type
        self.name = name
        self.value = value

    def set_value(self, value):
        self.value = value

    def __repr__(self):
        return f"<ResponseOption type={self.type!r} name={self.name!r} value={self.value!r}>"

    @classmethod
    def from_dict(cls, data: dict):
        type = SlashOptionType(data.get("type", 3))
        return cls(type=type, name=data["name"], value=data["value"])


class Component:
    def __init__(
        self,
        type: int = 1,
        *,
        components: List["Component"] = [],
        style: str = None,
        label: str = None,
        custom_id: int = None,
        url: str = None,
    ):
        self.type = type
        self.components = components
        self.style = style
        self.label = label
        self.custom_id = str(custom_id) if custom_id else None
        self.url = url

    def __repr__(self):
        kwargs = " ".join(f"{key}={value}" for key, value in self.__dict__.items() if value)
        return f"<{type(self).__name__} {kwargs}>"

    def to_dict(self):
        data = {"type": self.type}
        if self.type == 1:
            data["components"] = [c.to_dict() for c in self.components]
        else:  # elif type == 2:
            data["label"] = self.label
            data["style"] = self.style
            data["custom_id"] = self.custom_id
            if self.url:
                data["url"] = self.url
        return data

    @classmethod
    def from_dict(cls, data: dict):
        type = data.pop["type"]
        components = [cls.from_dict(c) for c in data.get("components", [])]
        style = data.get("style")
        label = data.get("label")
        custom_id = data.get("custom_id")
        url = data.get("url")
        return cls(
            type, components=components, style=style, label=label, custom_id=custom_id, url=url
        )


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


class InteractionResponse:
    def __init__(self, *, cog, data: dict):
        self.cog = cog
        self.bot = cog.bot
        self.http: SlashHTTP = cog.http
        self._state: discord.state.AutoShardedConnectionState = self.bot._connection
        self.id = int(data["id"])
        self.version = data["version"]
        self._token = data["token"]
        self._original_data = data

        self.guild_id = guild_id = discord.utils._get_as_snowflake(data, "guild_id")
        self.channel_id = discord.utils._get_as_snowflake(data, "channel_id")
        self.application_id = discord.utils._get_as_snowflake(data, "application_id")

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

    @property
    def guild(self) -> discord.Guild:
        return self.bot.get_guild(self.guild_id)

    @property
    def channel(self) -> discord.TextChannel:
        return self.bot.get_channel(self.channel_id)

    @property
    def created_at(self):
        return discord.utils.snowflake_time(self.id)

    async def send(
        self,
        content: str = None,
        *,
        embed: discord.Embed = None,
        embeds: List[discord.Embed] = [],
        tts: bool = False,
        allowed_mentions: discord.AllowedMentions = None,
        hidden: bool = False,
        delete_after: int = None,
    ):
        flags = 64 if hidden else None
        initial = not self.sent
        data = await self.http.send_message(
            self._token,
            self.id,
            type=4,
            initial_response=initial,
            content=content,
            embed=embed,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            tts=tts,
            flags=flags,
        )

        if not self.sent:
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
                log.exception("Failed to create message object for data:\n%r" % data, exc_info=e)
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
            type=5,
            initial_response=initial,
            flags=flags,
        )
        if not self.sent:
            self.sent = True
        self.deferred = True
        return data


class InteractionButton(InteractionResponse):
    def __init__(self, *, cog, data: dict):
        super().__init__(cog=cog, data=data)
        self.custom_id = self.interaction_data["custom_id"]
        self.component_type = self.interaction_data["component_type"]


class InteractionCommand(InteractionResponse):
    def __init__(self, *, cog, data: dict):
        super().__init__(cog=cog, data=data)
        self.command_name = self.interaction_data["name"]
        self.command_id = int(self.interaction_data["id"])
        self.options: List[ResponseOption] = []
        self._parse_options(
            self.interaction_data.get("options", []), self.interaction_data.get("resolved", {})
        )

    def __repr__(self) -> str:
        return f"<{type(self).__name__} id={self.id} command={self.command!r} channel={self.channel!r} author={self.author!r}>"

    @functools.cached_property
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
        return f"https://discord.com/channels/{guild_id}/{self.channel.id}/{self.id}"

    def _parse_options(self, options: List[dict], resolved: Dict[str, Dict[str, dict]]):
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
                        "Failed to handle option data for option:\n%r" % o, exc_info=error
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
