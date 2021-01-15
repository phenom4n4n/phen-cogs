from typing import Optional

from TagScriptEngine import Interpreter, adapter
from TagScriptEngine.interface import Block


class RequireBlock(Block):
    """
    The require block will attempt to convert the given parameter into a channel
    or role, using name or ID. If the user running the tag is not in the targeted
    channel or doesn't have the targeted role, the tag will stop processing and
    it will send the response if one is given. Multiple role or channel
    requirements can be given, and should be split by a ",".

    **Usage:** ``{require(<role,channel>):[response]}``

    **Aliases:** ``whitelist``

    **Payload:** response, None

    **Parameter:** role, channel

    **Usage:** ::

        {require(Moderator)}
        {require(#general, #bot-cmds):This tag can only be run in #general and #bot-cmds.}
        {require(757425366209134764, 668713062186090506, 737961895356792882):You aren't allowed to use this tag.}
    """

    def will_accept(self, ctx: Interpreter.Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return any([dec == "require", dec == "whitelist"])

    def process(self, ctx: Interpreter.Context) -> Optional[str]:
        if not ctx.verb.parameter:
            return None
        actions = ctx.response.actions.get("requires")
        if actions:
            return None
        ctx.response.actions["requires"] = {
            "items": [i.strip() for i in ctx.verb.parameter.split(",")],
            "response": ctx.verb.payload,
        }
        return ""


class BlacklistBlock(Block):
    """
    The blacklist block will attempt to convert the given parameter into a channel
    or role, using name or ID. If the user running the tag is in the targeted
    channel or has the targeted role, the tag will stop processing and
    it will send the response if one is given. Multiple role or channel
    requirements can be given, and should be split by a ",".

    **Usage:** ``{blacklist(<role,channel>):[response]}``

    **Payload:** response, None

    **Parameter:** role, channel

    **Usage:** ::

        {blacklist(Muted)}
        {blacklist(#support):This tag is not allowed in #support.}
        {blacklist(Tag Blacklist, 668713062186090506):You are blacklisted from using tags.}
    """

    def will_accept(self, ctx: Interpreter.Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return dec == "blacklist"

    def process(self, ctx: Interpreter.Context) -> Optional[str]:
        if not ctx.verb.parameter:
            return None
        actions = ctx.response.actions.get("blacklist")
        if actions:
            return None
        ctx.response.actions["blacklist"] = {
            "items": [i.strip() for i in ctx.verb.parameter.split(",")],
            "response": ctx.verb.payload,
        }
        return ""
