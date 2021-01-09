from typing import Optional

from TagScriptEngine import Interpreter, adapter
from TagScriptEngine.block.helpers import helper_parse_if
from TagScriptEngine.interface import Block


class SilentBlock(Block):
    # This is an undocumented block and should not be used.
    def will_accept(self, ctx: Interpreter.Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return any([dec == "silent", dec == "silence"])

    def process(self, ctx: Interpreter.Context) -> Optional[str]:
        if "silent" in ctx.response.actions.keys():
            return None
        if ctx.verb.parameter == None:
            value = True
        else:
            value = helper_parse_if(ctx.verb.parameter)
        ctx.response.actions["silent"] = value
        return ""
