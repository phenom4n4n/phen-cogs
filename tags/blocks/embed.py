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
