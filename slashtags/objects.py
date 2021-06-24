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
from typing import Optional

import discord
import TagScriptEngine as tse
from red_interactions import InteractionResponse, SlashCommand
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify

log = logging.getLogger("red.phenom4n4n.slashtags.objects")

__all__ = (
    "SlashTag",
    "FakeMessage",
    "SlashContext",
)


class SlashTag:
    __slots__ = (
        "cog",
        "config",
        "bot",
        "tagscript",
        "command_id",
        "guild_id",
        "author_id",
        "uses",
        "_real_tag",
    )

    def __init__(
        self,
        cog: commands.Cog,
        tagscript: str,
        *,
        guild_id: int = None,
        author_id: int = None,
        uses: int = 0,
        real: bool = True,
        command_id: int,
    ):
        self.cog = cog
        self.config: Config = cog.config
        self.bot: Red = cog.bot
        self.tagscript = tagscript

        self.command_id = command_id

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

    @property
    def command(self) -> SlashCommand:
        return self.cog.state.get_command(self.command_id)

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
        return f"{self.name_prefix} `{self}` added with {len(self.command.options)} arguments."

    @classmethod
    def from_dict(
        cls,
        cog: commands.Cog,
        data: dict,
        *,
        guild_id: int = None,
        real_tag: bool = True,
    ):
        try:
            command_id = data["command_id"]
        except KeyError:
            command_id = data["command"]["id"]
        return cls(
            cog,
            data["tag"],
            guild_id=guild_id,
            author_id=data["author_id"],
            uses=data.get("uses", 0),
            real=real_tag,
            command_id=command_id,
        )

    def to_dict(self):
        return {
            "author_id": self.author_id,
            "uses": self.uses,
            "tag": self.tagscript,
            "command_id": self.command_id,
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

    async def edit_options(self, ctx: commands.Context):
        old_options = self.command.options
        options = await self.cog.get_options(ctx, [])
        await self.edit(options=options)
        await ctx.send(
            f"{self.name_prefix} `{self}`'s arguments have been edited from {len(old_options)} to {len(options)} arguments."
        )

    async def edit_single_option(self, ctx: commands.Context, name: str):
        options = self.command.options
        option = discord.utils.get(options, name=name)
        if not option:
            await ctx.send(
                f'{self.name_prefix} `{self}` doesn\'t have an argument named "{name}".'
            )
            return
        added_required = not options[-1].required if len(options) > 2 else False
        try:
            new_option = await self.cog.get_option(ctx, added_required=added_required)
        except asyncio.TimeoutError:
            await ctx.send("Adding this argument timed out.", delete_after=15)
            return
        index = options.index(option)
        options.pop(index)
        options.insert(index, new_option)
        await self.command.edit(options=options)
        await ctx.send(f"Edited {self.name_prefix.lower()} `{self}`'s `{new_option}` argument.")


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
        destination = self.interaction or self.channel
        return destination.send(content, **kwargs)


class SlashContext(commands.Context):
    def __init__(self, *, interaction: InteractionResponse, **kwargs):
        self.interaction: InteractionResponse = interaction
        super().__init__(**kwargs)
        self.send = interaction.send

    def __repr__(self):
        return (
            f"<SlashContext interaction={self.interaction!r} invoked_with={self.invoked_with!r}>"
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
