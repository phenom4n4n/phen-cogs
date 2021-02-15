import discord
from typing import Optional
from redbot.core import commands, Config
from redbot.core.bot import Red
from TagScriptEngine import Interpreter, adapter


class Tag(object):
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
    ):
        self.cog = cog
        self.config: Config = cog.config
        self.bot: Red = cog.bot
        self.name: str = name
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
        seed_variables.update(uses=adapter.IntAdapter(self.uses))
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
        self = cls(
            cog,
            name,
            data["tag"],
            guild_id=guild_id,
            author_id=data.get("author_id", data.get("author")),
            uses=data.get("uses", 0),
            real=real_tag,
        )

        return self

    def to_dict(self):
        return {
            "author_id": self.author_id,
            "uses": self.uses,
            "tag": self.tagscript,
            "author": self.author_id,  # backwards compatability
        }

    async def delete(self):
        if self.guild_id:
            async with self.config.guild_from_id(self.guild_id).tags() as t:
                del e[self.name]
            del self.cog.guild_tag_cache[ctx.guild.id][self.name]
        else:
            async with self.config.tags() as e:
                del e[self.name]
            del self.cog.global_tag_cache[self.name]
