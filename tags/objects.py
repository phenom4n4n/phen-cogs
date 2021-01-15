import discord
from typing import Optional
from redbot.core import commands, Config
from redbot.core.bot import Red
from TagScriptEngine import Interpreter


class Tag(object):
    def __init__(
        self,
        cog: commands.Cog,
        guild: discord.Guild,
        name: str,
        tagscript: str,
        *,
        author: discord.User = None,
        author_id: int = None,
        uses: int = 0,
        real: bool = True,
    ):
        self.cog = cog
        self.config: Config = cog.config
        self.bot: Red = cog.bot
        self.guild: Optional[
            discord.Guild
        ] = guild  # guild may not be present when using `tag process`
        self.name: str = name
        self.tagscript: str = tagscript

        self.author: discord.User = author
        self.author_id: int = author.id if author else author_id
        self.uses: int = uses

        self._real_tag: bool = real

    def __str__(self) -> str:
        return self.name

    def __len__(self) -> int:
        return len(self.tagscript)

    def run(self, interpreter: Interpreter, **kwargs) -> Interpreter.Response:
        self.uses += 1
        return interpreter.process(self.tagscript, **kwargs)

    async def update_config(self):
        if self._real_tag and self.guild:
            async with self.config.guild(self.guild).tags() as t:
                t[self.name].update(uses=self.uses, tag=self.tagscript)

    @classmethod
    def from_dict(cls, cog: commands.Cog, guild: discord.Guild, name: str, data: dict):
        self = cls.__new__(cls)
        self.cog = cog
        self.config: Config = cog.config
        self.bot: Red = cog.bot
        self.guild: discord.Guild = guild
        self.name: str = name

        self.tagscript = data["tag"]
        self.author_id = author_id = data.get("author_id", data.get("author"))
        self.author = guild.get_member(author_id) if isinstance(guild, discord.Guild) else None
        self.uses = data.get("uses", 0)
        self._real_tag: bool = True

        return self

    def to_dict(self):
        return {
            "author_id": self.author_id,
            "uses": self.uses,
            "tag": self.tagscript,
            "author": self.author_id,
        }
