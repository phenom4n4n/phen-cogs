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

from typing import List, Optional

import discord
import TagScriptEngine as tse
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_list, humanize_number, inline, pagify

from .errors import TagAliasError

hn = humanize_number
ALIAS_LIMIT = 10


class Tag:
    __slots__ = (
        "cog",
        "config",
        "bot",
        "name",
        "_aliases",
        "tagscript",
        "guild_id",
        "author_id",
        "uses",
        "_real_tag",
    )

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
        self._aliases = aliases.copy()
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
        return f"<Tag name={self.name!r} guild_id={self.guild_id} length={len(self)} aliases={self.aliases!r}>"

    @property
    def cache_path(self) -> dict:
        return (
            self.cog.guild_tag_cache[self.guild_id] if self.guild_id else self.cog.global_tag_cache
        )

    @property
    def config_path(self):
        return self.config.guild_from_id(self.guild_id) if self.guild_id else self.config

    @property
    def guild(self) -> Optional[discord.Guild]:
        return self.bot.get_guild(self.guild_id)

    @property
    def author(self) -> Optional[discord.User]:
        return self.bot.get_user(self.author_id)

    @property
    def name_prefix(self) -> str:
        return "Tag" if self.guild_id else "Global tag"

    @property
    def aliases(self) -> List[str]:
        return self._aliases.copy()

    def run(self, seed_variables: dict, **kwargs) -> tse.Response:
        self.uses += 1
        seed_variables["uses"] = tse.IntAdapter(self.uses)
        return self.cog.engine.process(
            self.tagscript, seed_variables, cooldown_key=f"{self.guild_id}:{self.name}", **kwargs
        )

    async def update_config(self):
        if self._real_tag:
            async with self.config_path.tags() as t:
                t[self.name] = self.to_dict()

    async def initialize(self) -> str:
        self.add_to_cache()
        await self.update_config()
        return f"{self.name_prefix} `{self}` added."

    def add_to_cache(self):
        path = self.cache_path
        path[self.name] = self
        for alias in self.aliases:
            path[alias] = self

    def remove_from_cache(self):
        path = self.cache_path
        del path[self.name]
        for alias in self.aliases:
            try:
                del path[alias]
            except KeyError:
                pass

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

    async def delete(self) -> str:
        async with self.config_path.tags() as t:
            del t[self.name]
        self.remove_from_cache()
        return f"{self.name_prefix} `{self}` deleted."

    async def add_alias(self, alias: str) -> str:
        if len(self.aliases) >= ALIAS_LIMIT:
            raise TagAliasError(
                f"This {self.name_prefix.lower()} already has the maximum of {ALIAS_LIMIT} aliases."
            )
        elif alias in self.aliases:
            raise TagAliasError(f"`{alias}` is already an alias for `{self}`.")
        elif aliased_tag := self.cache_path.get(alias):
            raise TagAliasError(f"`{alias}` is already an alias for `{aliased_tag}`.")

        self._aliases.append(alias)
        self.cache_path[alias] = self
        await self.update_config()
        return f"`{alias}` has been added as an alias to {self.name_prefix.lower()} `{self}`."

    async def remove_alias(self, alias: str) -> str:
        if alias not in self.aliases:
            raise TagAliasError(f"`{alias}` is not a valid alias for `{self}`.")

        self._aliases.remove(alias)
        del self.cache_path[alias]
        await self.update_config()
        return f"Alias `{alias}` removed from {self.name_prefix.lower()} `{self}`."

    async def edit_tagscript(self, tagscript: str) -> str:
        old_tagscript = len(self.tagscript)
        self.tagscript = tagscript
        await self.update_config()
        return f"Edited `{self}`'s tagscript from **{hn(old_tagscript)}** to **{hn(len(self.tagscript))}** characters."

    async def get_info(self, ctx: commands.Context) -> discord.Embed:
        desc = [
            f"Author: {self.author.mention if self.author else self.author_id}",
            f"Uses: **{self.uses}**",
            f"Length: **{hn(len(self))}**",
        ]
        if self.aliases:
            desc.append(humanize_list([inline(alias) for alias in self.aliases]))
        e = discord.Embed(
            color=await ctx.embed_color(),
            title=f"{self.name_prefix} `{self}` Info",
            description="\n".join(desc),
        )
        if self.guild_id:
            e.set_author(name=ctx.guild, icon_url=ctx.guild.icon_url)
        else:
            e.set_author(name=ctx.me, icon_url=ctx.me.avatar_url)
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


class SilentContext(commands.Context):
    """Modified Context class to prevent command output to users."""

    async def send(self, *args, **kwargs):
        pass

    async def reply(self, *args, **kwargs):
        pass
