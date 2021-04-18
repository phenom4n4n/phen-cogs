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

from typing import Optional, List

import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbor.core.utils.chat_formatting import humanize_number as hn
from TagScriptEngine import Interpreter, IntAdapter

from .errors import *

ALIAS_LIMIT = 10


class Tag:
    def __init__(
        self,
        cog: commands.Cog,
        name: str,
        tagscript: str,
        *,
        guild_id: int = None,
        author_id: int = None,
        uses: int = 0,
        real: bool = True,
        aliases: List[str] = [],
    ):
        self.cog = cog
        self.config: Config = cog.config
        self.bot: Red = cog.bot
        self.name: str = name
        self.aliases = aliases
        self.tagscript: str = tagscript

        self.guild_id = guild_id
        self.author_id: int = author_id
        self.uses: int = uses

        self._real_tag: bool = real

    def __str__(self) -> str:
        return self.name

    def __len__(self) -> int:
        return len(self.tagscript)

    def __hash__(self) -> int:
        return hash(self.name)

    def __repr__(self) -> str:
        return f"<Tag name={self.name!r} length={len(self)} aliases={self.aliases!r}>"

    @property
    def cache_path(self) -> dict:
        return self.cog.guild_tag_cache[self.guild_id] if self.guild_id else self.cog.global_tag_cache

    @property
    def config_path(self):
        return self.config.guild_from_id(self.guild_id) if self.guild_id else self.config

    @property
    def guild(self) -> Optional[discord.Guild]:
        if self.guild_id:
            if guild := self.bot.get_guild(self.guild_id):
                return guild

    @property
    def author(self) -> Optional[discord.User]:
        return self.bot.get_user(self.author_id)

    @property
    def name_prefix(self):
        return "Tag" if self.guild_id else "Global tag"

    def run(
        self, interpreter: Interpreter, seed_variables: dict = {}, **kwargs
    ) -> Interpreter.Response:
        self.uses += 1
        seed_variables.update(uses=IntAdapter(self.uses))
        return interpreter.process(self.tagscript, seed_variables, **kwargs)

    async def update_config(self):
        if self._real_tag:
            async with self.config_path.tags() as t:
                t[self.name] = self.to_dict()

    @classmethod
    def from_dict(
        cls,
        cog: commands.Cog,
        name: str,
        data: dict,
        *,
        guild_id: int = None,
        real_tag: bool = True,
    ):
        return cls(
            cog,
            name,
            data["tag"],
            guild_id=guild_id,
            author_id=data.get("author_id", data.get("author")),
            uses=data.get("uses", 0),
            real=real_tag,
            aliases=data.get("aliases", []),
        )

    def to_dict(self):
        return {
            "author_id": self.author_id,
            "uses": self.uses,
            "tag": self.tagscript,
            "aliases": self.aliases,
        }

    async def delete(self):
        async with self.config_path.tags() as t:
            del t[self.name]
        self.remove_from_cache()

    def add_to_cache(self):
        path = self.cache_path
        path[self.name] = self
        for alias in self.aliases:
            path[alias] = self

    def remove_from_cache(self):
        path = self.cache_path
        del path[self.guild_id][self.name]
        for alias in self.aliases:
            del path[alias]

    async def add_alias(self, alias: str):
        if len(tag.aliases) >= ALIAS_LIMIT:
            raise TagAliasError(f"This tag already has the maximum of {ALIAS_LIMIT} aliases.")

        self.aliases.append(alias)
        self.cache_path[alias] = tag
        await self.update_config()

    async def remove_alias(self, alias: str):
        if alias not in self.aliases:
            raise TagAliasError(f"`{alias}` is not a valid alias for `{tag}`.")

        self.aliases.remove(alias)
        del self.cache_path[alias]
        await self.update_config()

    async def edit_tagscript(self, tagscript: str):
        old_tagscript = len(self.tagscript)
        self.tagscript = tagscript
        await self.update_config()
        return f"Edited `{self.name}`'s tagscript from **{hn(old_tagscript)}** to **{hn(len(self.tagscript))}** characters."
