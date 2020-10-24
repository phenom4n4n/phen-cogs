import discord
from redbot.core import commands
from TagScriptEngine import Interpreter, adapter, block


class Tag(object):
    def __init__(
        self,
        name: str,
        tagscript: str,
        *,
        invoker: discord.Member = None,
        author: discord.Member = None,
        author_id: int = None,
        uses: int = 0,
        ctx: commands.Context = None
    ):
        self.name = name
        self.tagscript = tagscript
        self.invoker = invoker
        self.author = author
        self.author_id = author_id
        self.uses = uses
        self.ctx = ctx

    def __str__(self) -> str:
        return self.name

    def __len__(self) -> int:
        return len(self.tagscript)

    def run(self, interpreter: Interpreter, **kwargs) -> Interpreter.Response:
        return interpreter.process(self.tagscript, **kwargs)

    @classmethod
    def from_dict(cls, name: str, data: dict, *, ctx: commands.Context):
        self = cls.__new__(cls)
        self.name = name
        self.tagscript = data["tag"]
        self.uses = data.get("uses")
        self.invoker = data.get("invoker")
        self.author_id = data.get("author_id", data.get("author"))
        if ctx:
            self.ctx = ctx
            self.author = ctx.guild.get_member(data.get("author"))
        else:
            self.ctx = None
            self.author = None
        return self
