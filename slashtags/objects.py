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

from typing import List, Optional, Union

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from TagScriptEngine import IntAdapter, Interpreter, StringAdapter

from .http import SlashHTTP
from .models import InteractionResponse, SlashOptionType


class SlashOptionChoice:
    def __init__(self, name: str, value: Union[str, int]):
        self.name: name
        self.value: value

    def to_dict(self):
        return {"name": self.name, "value": self.value}

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data["name"], data["value"])


class SlashOption:
    def __init__(
        self,
        *,
        option_type: SlashOptionType = SlashOptionType.STRING,
        name: str,
        description: str,
        required: bool = False,
        choices: List[SlashOptionChoice] = [],
        options: list = [],
    ):
        if not isinstance(option_type, SlashOptionType):
            option_type = SlashOptionType(option_type)
        self.type = option_type
        self.name = name
        self.description = description
        self.required = required
        self.choices = choices
        self.options = options

    def to_dict(self):
        data = {
            "type": self.type.value,
            "name": self.name,
            "description": self.description,
            "required": self.required,
        }

        if self.choices:
            data["choices"] = [c.to_dict() for c in self.choices]
        if self.options:
            data["options"] = [o.to_dict() for o in self.options]
        return data

    @classmethod
    def from_dict(cls, data: dict):
        choices = [SlashOptionChoice.from_dict(choice) for choice in data.get("choices", [])]

        options = [cls.from_dict(option) for option in data.get("options", [])]
        return cls(
            option_type=SlashOptionType(data["type"]),
            name=data["name"],
            description=data["description"],
            required=data.get("required", False),
            choices=choices,
            options=options,
        )


class SlashCommand:
    def __init__(
        self,
        cog,
        *,
        id: int = None,
        application_id: int = None,
        name: str,
        description: str,
        guild_id: int = None,
        options: List[SlashOption] = list,
    ):
        self.cog = cog
        self.http = cog.http

        self.id = id
        self.application_id = application_id
        self.name = name
        self.description = description
        self.guild_id = guild_id
        self.options = options

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return "<SlashCommand id={0.id} name={0.name!r} description={0.description!r} guild_id={0.guild_id!r}>".format(
            self
        )

    @property
    def qualified_name(self) -> str:
        return self.name

    def to_request(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "options": [o.to_dict() for o in self.options],
        }

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "application_id": self.application_id,
            "name": self.name,
            "description": self.description,
            "options": [o.to_dict() for o in self.options],
            "guild_id": self.guild_id,
        }

    @classmethod
    def from_dict(cls, cog, data: dict):
        id = discord.utils._get_as_snowflake(data, "id")
        application_id = discord.utils._get_as_snowflake(data, "application_id")
        name = data["name"]
        description = data["description"]
        options = [SlashOption.from_dict(o) for o in data.get("options", [])]
        guild_id = discord.utils._get_as_snowflake(data, "guild_id")
        return cls(
            cog,
            id=id,
            application_id=application_id,
            name=name,
            description=description,
            guild_id=guild_id,
            options=options,
        )

    def _parse_response_data(self, data: dict):
        _id = discord.utils._get_as_snowflake(data, "id")
        application_id = discord.utils._get_as_snowflake(data, "application_id")
        name = data.get("name")
        description = data.get("description")
        if _id:
            self.id = _id
        if application_id:
            self.application_id = application_id
        if name:
            self.name = name
        if description:
            self.description = description
        self.options = [SlashOption.from_dict(o) for o in data.get("options", [])]

    async def register(self):
        if self.guild_id:
            data = await self.http.add_guild_slash_command(self.guild_id, self.to_request())
        else:
            data = await self.http.add_slash_command(self.to_request())
        self._parse_response_data(data)

    async def edit(
        self, *, name: str = None, description: str = None, options: List[SlashOption] = None
    ):
        payload = {}
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        if options:
            payload["options"] = [o.to_dict() for o in options]

        if self.guild_id:
            data = await self.http.edit_guild_slash_command(self.guild_id, self.id, payload)
        else:
            data = await self.http.edit_slash_command(self.id, payload)
        self._parse_response_data(data)

    async def delete(self):
        self.remove_from_cache()
        if self.guild_id:
            await self.http.remove_guild_slash_command(self.guild_id, self.id)
        else:
            await self.http.remove_slash_command(self.id)

    def remove_from_cache(self):
        try:
            del self.cog.command_cache[self.id]
        except KeyError:
            pass


class SlashTag:
    def __init__(
        self,
        cog: commands.Cog,
        tagscript: str,
        *,
        options: list = [],
        guild_id: int = None,
        author_id: int = None,
        uses: int = 0,
        real: bool = True,
        command: SlashCommand,
    ):
        self.cog = cog
        self.http: SlashHTTP = cog.http
        self.config: Config = cog.config
        self.bot: Red = cog.bot
        self.tagscript = tagscript

        self.command = command

        self.guild_id = guild_id
        self.author_id = author_id
        self.uses = uses

        self._real_tag = real

    def __str__(self) -> str:
        return self.name

    def __len__(self) -> int:
        return len(self.tagscript)

    def __bool__(self) -> bool:
        return True

    def __repr__(self):
        return "<SlashTag id={0.id} name={0.name!r} command={0.command!r} author={0.author!r}>".format(
            self
        )

    @property
    def name(self):
        return self.command.name

    @property
    def id(self):
        return self.command.id

    @property
    def description(self):
        return self.command.description

    @property
    def guild(self) -> Optional[discord.Guild]:
        return self.bot.get_guild(self.guild_id)

    @property
    def author(self) -> Optional[discord.User]:
        return self.bot.get_user(self.author_id)

    def run(
        self, interpreter: Interpreter, seed_variables: dict = {}, **kwargs
    ) -> Interpreter.Response:
        self.uses += 1
        seed_variables.update(uses=IntAdapter(self.uses))
        return interpreter.process(self.tagscript, seed_variables, **kwargs)

    async def update_config(self):
        if self._real_tag:
            if self.guild_id:
                async with self.config.guild_from_id(self.guild_id).tags() as t:
                    t[str(self.id)] = self.to_dict()
            else:
                async with self.config.tags() as t:
                    t[str(self.id)] = self.to_dict()

    @classmethod
    def from_dict(
        cls,
        cog: commands.Cog,
        data: dict,
        *,
        guild_id: int = None,
        real_tag: bool = True,
    ):
        return cls(
            cog,
            data["tag"],
            guild_id=guild_id,
            author_id=data["author_id"],
            uses=data.get("uses", 0),
            real=real_tag,
            command=SlashCommand.from_dict(cog, data["command"]),
        )

    def to_dict(self):
        return {
            "author_id": self.author_id,
            "uses": self.uses,
            "tag": self.tagscript,
            "command": self.command.to_dict(),
        }

    async def delete(self):
        try:
            await self.command.delete()
        except discord.NotFound:
            pass
        if self.guild_id:
            async with self.config.guild_from_id(self.guild_id).tags() as t:
                del t[str(self.id)]
        else:
            async with self.config.tags() as t:
                del t[str(self.id)]
        self.remove_from_cache()

    def remove_from_cache(self):
        try:
            if self.guild_id:
                del self.cog.guild_tag_cache[self.guild_id][self.id]
            else:
                del self.cog.global_tag_cache[self.id]
        except KeyError:
            pass


def implement_partial_methods(cls):
    msg = discord.Message
    for name in discord.Message.__slots__:
        func = getattr(msg, name)
        setattr(cls, name, func)
    return cls


@implement_partial_methods
class FakeMessage(discord.Message):
    REIMPLEMENTS = {
        "reactions": [],
        "mentions": [],
        "attachments": [],
        "stickers": [],
        "embeds": [],
        "flags": discord.MessageFlags._from_value(0),
    }

    def __init__(
        self,
        content: str,
        *,
        channel: discord.TextChannel,
        author: discord.Member,
        id: int,
        state,
    ):
        self._state = state
        self.id = id
        self.channel = channel
        self.guild = channel.guild

        self.content = content
        self.author = author

        for name, value in self.REIMPLEMENTS.items():
            if not hasattr(self, name):
                setattr(self, name, value)

        for item in self.__slots__:
            if not hasattr(self, item):
                setattr(self, item, None)

    @classmethod
    def from_interaction(cls, interaction, content: str):
        return cls(
            content,
            state=interaction._state,
            id=interaction.id,
            channel=interaction.channel,
            author=interaction.author,
        )


class SlashContext(commands.Context):
    def __init__(self, *, interaction: InteractionResponse, **kwargs):
        self.interaction: InteractionResponse = interaction
        super().__init__(**kwargs)
        self.send = interaction.send

    def __repr__(self):
        return (
            "<SlashContext interaction={0.interaction!r} invoked_with={0.invoked_with!r}>".format(
                self
            )
        )

    @classmethod
    def from_interaction(cls, interaction: InteractionResponse):
        args_values = [o.value for o in interaction.options]
        return cls(
            interaction=interaction,
            message=interaction,
            bot=interaction.bot,
            args=args_values,
            prefix="/",
            command=interaction.command,
            invoked_with=interaction.command_name,
        )

    async def tick(self):
        await self.interaction.send("✅", hidden=True)
