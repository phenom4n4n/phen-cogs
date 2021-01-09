from typing import Optional

from TagScriptEngine import Interpreter, adapter
from TagScriptEngine.interface import Block


class CommandBlock(Block):
    """
    Run a command as if the tag invoker had ran it. Only 3 command blocks can be used in a tag.

    Usage: ``{command:<command>}``

    Aliases: ``c, com, command``

    Payload: command

    Parameter: None
    """
    
    def will_accept(self, ctx: Interpreter.Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return any([dec == "c", dec == "com", dec == "command"])

    def process(self, ctx: Interpreter.Context) -> Optional[str]:
        if not ctx.verb.payload:
            return None
        actions = ctx.response.actions.get("commands")
        if actions:
            if len(actions) >= 3:
                return f"`COMMAND LIMIT REACHED (3)`"
            ctx.response.actions["commands"].append(ctx.verb.payload)
        else:
            ctx.response.actions["commands"] = []
            ctx.response.actions["commands"].append(ctx.verb.payload)
        return ""
