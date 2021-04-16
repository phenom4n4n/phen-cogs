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
from TagScriptEngine import Interpreter, IntAdapter


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

    @property
    def guild(self) -> Optional[discord.Guild]:
        if self.guild_id:
            if guild := self.bot.get_guild(self.guild_id):
                return guild

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
                    t[self.name] = self.to_dict()
            else:
                async with self.config.tags() as t:
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
        if self.guild_id:
            async with self.config.guild_from_id(self.guild_id).tags() as t:
                del t[self.name]
        else:
            async with self.config.tags() as t:
                del t[self.name]
        self.remove_from_cache()

    def remove_from_cache(self):
        if self.guild:
            path = self.cog.guild_tag_cache[self.guild_id]
        else:
            path = self.cog.global_tag_cache

        try:
            del path[self.guild_id][self.name]
            for alias in aliases:
                del path[alias]
        except KeyError:
            pass
