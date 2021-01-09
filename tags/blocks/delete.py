from typing import Optional

from TagScriptEngine import Interpreter, adapter
from TagScriptEngine.block.helpers import helper_parse_if
from TagScriptEngine.interface import Block


class DeleteBlock(Block):
    """
    Delete blocks will delete the invocation message if the given parameter is true. If there is no parameter i.e. ``{delete}`` it will default to true.

    Usage: ``{delete([bool])``

    Payload: None

    Parameter: bool, None
    """

    def will_accept(self, ctx: Interpreter.Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return dec == "delete"

    def process(self, ctx: Interpreter.Context) -> Optional[str]:
        if "delete" in ctx.response.actions.keys():
            return None
        if ctx.verb.parameter == None:
            value = True
        else:
            value = helper_parse_if(ctx.verb.parameter)
        ctx.response.actions["delete"] = value
        return ""
