from typing import Optional

from TagScriptEngine import Interpreter, adapter
from TagScriptEngine.interface import Block


class ReactBlock(Block):
    """
    The react block will react with up to 5 emoji to the tag response message. The given emoji can be custom or unicode emoji. Emojis can be split with ",".

    Usage: ``{react(<emoji,emoji>)}``

    Payload: None

    Parameter: emoji
    """

    def will_accept(self, ctx: Interpreter.Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return dec == "react"

    def process(self, ctx: Interpreter.Context) -> Optional[str]:
        if not ctx.verb.parameter:
            return None
        ctx.response.actions["react"] = [arg.strip() for arg in ctx.verb.parameter.split(",")[:5]]
        return ""


class ReactUBlock(Block):
    """
    The react block will react with up to 5 emoji to the tag invocation message. The given emoji can be custom or unicode emoji. Emojis can be split with ",".

    Usage: ``{reactu(<emoji,emoji>)}``

    Payload: None

    Parameter: emoji
    """

    def will_accept(self, ctx: Interpreter.Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return dec == "reactu"

    def process(self, ctx: Interpreter.Context) -> Optional[str]:
        if not ctx.verb.parameter:
            return None
        ctx.response.actions["reactu"] = [arg.strip() for arg in ctx.verb.parameter.split(",")[:5]]
        return ""
