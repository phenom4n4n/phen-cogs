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

import logging
from typing import List, Optional, Union

import discord
import TagScriptEngine as tse
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify

from .http import SlashHTTP
from .models import InteractionResponse, SlashOptionType

log = logging.getLogger("red.phenom4n4n.slashtags.objects")

__all__ = (
    "SlashOptionChoice",
    "SlashOption",
    "SlashCommand",
    "SlashTag",
    "FakeMessage",
    "SlashContext",
)


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
    def cache_path(self) -> dict:
        return (
            self.cog.guild_tag_cache[self.guild_id] if self.guild_id else self.cog.global_tag_cache
        )

    @property
    def config_path(self):
        return self.config.guild_from_id(self.guild_id) if self.guild_id else self.config

    @property
    def name_prefix(self):
        return "Slash tag" if self.guild_id else "Global slash tag"

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
        self, interpreter: tse.Interpreter, seed_variables: dict = {}, **kwargs
    ) -> tse.Response:
        self.uses += 1
        seed_variables.update(uses=tse.IntAdapter(self.uses))
        return interpreter.process(self.tagscript, seed_variables, **kwargs)

    async def update_config(self):
        if self._real_tag:
            async with self.config_path.tags() as t:
                t[str(self.id)] = self.to_dict()

    async def initialize(self) -> str:
        self.add_to_cache()
        await self.update_config()
        return f"{self.name_prefix} `{self}` added with {len(self.command.options)} options."

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

    async def delete(self) -> str:
        try:
            await self.command.delete()
        except discord.NotFound:
            pass
        async with self.config_path.tags() as t:
            del t[str(self.id)]
        self.remove_from_cache()
        return f"{self.name_prefix} `{self}` deleted."

    def remove_from_cache(self):
        try:
            del self.cache_path[self.id]
        except KeyError:
            pass

    def add_to_cache(self):
        self.cache_path[self.id] = self

    async def edit(self, **kwargs):
        await self.command.edit(**kwargs)
        await self.update_config()

    async def get_info(self, ctx: commands.Context) -> discord.Embed:
        desc = [
            f"Author: {self.author.mention if self.author else self.author_id}",
            f"Uses: {self.uses}",
            f"Length: {len(self)}",
        ]
        e = discord.Embed(
            color=await ctx.embed_color(),
            title=f"{self.name_prefix} `{self}` Info",
            description="\n".join(desc),
        )
        c = self.command
        command_info = [
            f"ID: `{c.id}`",
            f"Name: {c.name}",
            f"Description: {c.description}",
        ]
        e.add_field(name="Command", value="\n".join(command_info), inline=False)

        option_info = []
        for o in c.options:
            option_desc = [
                f"**{o.name}**",
                f"Description: {o.description}",
                f"Type: {o.type.name.title()}",
                f"Required: {o.required}",
            ]
            option_info.append("\n".join(option_desc))
        if option_info:
            e.add_field(name="Options", value="\n".join(option_info), inline=False)

        e.set_author(name=ctx.guild, icon_url=ctx.guild.icon_url)
        return e

    async def send_info(self, ctx: commands.Context) -> discord.Message:
        return await ctx.send(embed=await self.get_info(ctx))

    async def send_raw_tagscript(self, ctx: commands.Context):
        tagscript = discord.utils.escape_markdown(self.tagscript)
        for page in pagify(tagscript):
            await ctx.send(
                page,
                allowed_mentions=discord.AllowedMentions.none(),
            )

    async def edit_tagscript(self, tagscript: str) -> str:
        old_tagscript = self.tagscript
        self.tagscript = tagscript
        await self.update_config()
        return f"{self.name_prefix} `{self}`'s tagscript has been edited from {len(old_tagscript)} to {len(tagscript)} characters."

    async def edit_name(self, name: str) -> str:
        old_name = self.name
        await self.edit(name=name)
        return f"Renamed `{old_name}` to `{name}`."
    
    async def edit_description(self, description: str) -> str:
        await self.edit(description=description)
        return f"Edited {self.name_prefix.lower()} `{self}`'s description."

    async def edit_options(self, ctx: commands.Context) -> str:
        old_options = self.command.options
        options = await self.cog.get_options(ctx, [])
        await self.edit(options=options)
        await ctx.send(
            f"{self.name_prefix} `{self}`'s arguments have been edited from {len(old_options)} to {len(options)} arguments."
        )


def maybe_set_attr(cls, name, attr):
    if not hasattr(cls, name):
        setattr(cls, name, attr)


def implement_methods(parent):
    def wrapper(cls):
        log.debug("implementing %r methods on %r" % (parent, cls))

        for name in getattr(parent, "__slots__", []):
            func = getattr(parent, name)
            maybe_set_attr(cls, name, func)

        for name, attr in getattr(parent, "__dict__", {}).items():
            maybe_set_attr(cls, name, attr)

        return cls

    return wrapper


@implement_methods(discord.Message)
class FakeMessage(discord.Message):
    log.debug("FakeMessage defined")

    REIMPLEMENTS = {
        "reactions": [],
        "mentions": [],
        "attachments": [],
        "stickers": [],
        "embeds": [],
        "flags": discord.MessageFlags._from_value(0),
        "_edited_timestamp": None,
    }

    def __init__(
        self,
        content: str,
        *,
        channel: discord.TextChannel,
        author: discord.Member,
        id: int,
        interaction: InteractionResponse = None,
        state,
    ):
        self._state = state
        self.id = id
        self.channel = channel
        self.interaction = interaction

        self.content = content
        self.author = author

        for name, attr in self.REIMPLEMENTS.items():
            maybe_set_attr(self, name, attr)

    @classmethod
    def from_interaction(cls, interaction: InteractionResponse, content: str):
        return cls(
            content,
            state=interaction._state,
            id=interaction.id,
            channel=interaction.channel,
            author=interaction.author,
            interaction=interaction,
        )

    def to_reference(self, *args, **kwargs):
        # return None to prevent reply since interaction responses already reply (visually)
        # additionally, replying to an interaction response raises
        # message_reference: Unknown message
        return

    def reply(self, content: str = None, **kwargs):
        try:
            del kwargs["reference"]  # this shouldn't be passed when replying but it might be
        except KeyError:
            pass
        destination = self.interaction if self.interaction else self.channel
        return destination.send(content, **kwargs)


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
