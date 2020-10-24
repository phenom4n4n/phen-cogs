from typing import Optional
import json
from TagScriptEngine import Interpreter, adapter
from TagScriptEngine.block.helpers import helper_parse_if
from TagScriptEngine.interface import Block
from discord import Embed

class EmbedBlock(Block):
    def will_accept(self, ctx: Interpreter.Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return dec == "embed"

    def process(self, ctx: Interpreter.Context) -> Optional[str]:
        if "embed" in ctx.response.actions.keys() or ctx.verb.payload is None:
            return None
        try:
            data = json.loads(ctx.verb.payload)
        except json.decoder.JSONDecodeError:
            return None
        if data.get("embed"):
            data = data["embed"]
        if data.get("timestamp"):
            data["timestamp"] = data["timestamp"].strip("Z")
        try:
            e = Embed.from_dict(data)
        except Exception:
            return None
        ctx.response.actions["embed"] = e
        return ""
