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

from TagScriptEngine import Interpreter, Block


class CommandBlock(Block):
    """
    Run a command as if the tag invoker had ran it. Only 3 command
    blocks can be used in a tag.

    **Usage:** ``{command:<command>}``

    **Aliases:** ``c, com, command``

    **Payload:** command

    **Parameter:** None

    **Examples:** ::

        {c:ping}
        # invokes ping command

        {c:kick {target(id)} Chatflood/spam}
        # invokes ban command on the pinged user with the reason as "Chatflood/spam"

        {c:nick edit {args}}
        # makes a tag that aliases to the command `nick edit`
    """

    def will_accept(self, ctx: Interpreter.Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return any([dec == "c", dec == "com", dec == "command"])

    def process(self, ctx: Interpreter.Context) -> Optional[str]:
        if not ctx.verb.payload:
            return None
        command = ctx.verb.payload.strip()
        actions = ctx.response.actions.get("commands")
        if actions:
            if len(actions) >= 3:
                return f"`COMMAND LIMIT REACHED (3)`"
            ctx.response.actions["commands"].append(command)
        else:
            ctx.response.actions["commands"] = []
            ctx.response.actions["commands"].append(command)
        return ""


class OverrideBlock(Block):
    """
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

    **Examples:** ::

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
        overrides = ctx.response.actions.get(
            "overrides", {"admin": False, "mod": False, "permissions": False}
        )
        overrides[param] = True
        ctx.response.actions["overrides"] = overrides
        return ""
