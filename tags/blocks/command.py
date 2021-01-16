from typing import Optional

from TagScriptEngine import Interpreter, adapter
from TagScriptEngine.interface import Block


class CommandBlock(Block):
    """
    Run a command as if the tag invoker had ran it. Only 3 command 
    blocks can be used in a tag.

    **Usage:** ``{command:<command>}``

    **Aliases:** ``c, com, command``

    **Payload:** command

    **Parameter:** None

    **Example:** ::

        {c:ping}
        # invokes ping command

        {c:kick {target(id)} Chatflood/spam}
        # invokes ban command on the pinged user with the reason as "Chatflood/spam"
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

class OverrideBlock(Block):
    """
    .. warning:: This block is incomplete and cannot be used yet.

    Override a command's permission requirements. This can override 
    mod, admin, or general user permission requirements when running commands 
    with the :ref:`CommandBlock`. Passing no parameter will default to overriding 
    all permissions.

    In order to add a tag with the override block, the tag author must have ``Manage 
    Server`` permissions.

    This will not override bot owner commands or command checks.

    **Usage:** ``{override(["admin"|"mod"|"permissions"]):[command]}``

    **Payload:** command

    **Parameter:** "admin", "mod", "permissions"

    **Example:** ::

        {override}
        # overrides all commands and permissions

        {override(admin)}
        # overrides commands that require the admin role

        {override(permissions)}
        {override(mod)}
        # overrides commands that require the mod role or have user permission requirements
    """

    def will_accept(self, ctx: Interpreter.Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return dec == "override"

    def process(self, ctx: Interpreter.Context) -> Optional[str]:
        param = ctx.verb.parameter
        if not param:
            ctx.response.actions["overrides"] = {"admin": True, "mod": True, "permissions": True}
            return ""

        param = param.strip().lower()
        if param not in ("admin", "mod", "permissions"):
            return None
        overrides = ctx.response.actions.get("overrides", {"admin": False, "mod": False, "permissions": False})
        overrides[param] = True
        ctx.response.actions["overrides"] = overrides
        return ""