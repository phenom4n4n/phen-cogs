from typing import Optional
from discord import AllowedMentions
from TagScriptEngine import Interpreter, adapter
from TagScriptEngine.interface import Block


class AllowedMentionsBlock(Block):
    """
    .. warning:: This block is incomplete and cannot be used yet.
    """

    def will_accept(self, ctx: Interpreter.Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return dec == "allowedmentions"

    def process(self, ctx: Interpreter.Context) -> Optional[str]:
        if not (param := ctx.verb.parameter):
            return None
        param = param.strip().lower()
        allowed_mentions = ctx.response.actions.get("allowed_mentions", AllowedMentions(everyone=False, users=True, roles=False, replied_user=True))
