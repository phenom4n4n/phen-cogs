from typing import Optional

from TagScriptEngine import Interpreter, adapter
from TagScriptEngine.interface import Block


class CommandBlock(Block):
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