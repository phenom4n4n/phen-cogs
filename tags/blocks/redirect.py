from typing import Optional

from TagScriptEngine import Interpreter, adapter
from TagScriptEngine.interface import Block


class RedirectBlock(Block):
    def will_accept(self, ctx: Interpreter.Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return dec == "redirect"

    def process(self, ctx: Interpreter.Context) -> Optional[str]:
        if not ctx.verb.parameter:
            return None
        if ctx.verb.parameter.lower() == "dm":
            target = "dm"
        else:
            target = ctx.verb.parameter.strip()
        ctx.response.actions["target"] = target
        return ""
