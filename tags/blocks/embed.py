from typing import Optional
import json
from TagScriptEngine import Interpreter, adapter
from TagScriptEngine.block.helpers import helper_parse_if
from TagScriptEngine.interface import Block
from discord import Embed


class EmbedBlock(Block):
    """
    An embed block will send an embed in the tag response using properly formatted json.

    Usage: ``{embed(<json>)}``

    Payload: None

    Parameter: json

    Example::

        {embed({"title":"Hello!", "description":"This is a test embed."})}
    """

    def will_accept(self, ctx: Interpreter.Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return dec == "embed"

    def process(self, ctx: Interpreter.Context) -> Optional[str]:
        if "embed" in ctx.response.actions.keys() or ctx.verb.parameter is None:
            return None
        if not ctx.verb.parameter.startswith("{"):
            ctx.verb.parameter = "{" + ctx.verb.parameter
        if not ctx.verb.parameter.endswith("}"):
            ctx.verb.parameter = ctx.verb.parameter + "}"
        try:
            data = json.loads(ctx.verb.parameter)
        except json.decoder.JSONDecodeError as error:
            return str(error)
        if data.get("embed"):
            data = data["embed"]
        if data.get("timestamp"):
            data["timestamp"] = data["timestamp"].strip("Z")
        try:
            e = Embed.from_dict(data)
        except Exception as error:
            return str(error)
        try:
            length = len(e)
        except Exception as error:
            return str(error)
        if length > 6000:
            return f"`MAX EMBED LENGTH REACHED ({length}/6000)`"
        ctx.response.actions["embed"] = e
        return ""
