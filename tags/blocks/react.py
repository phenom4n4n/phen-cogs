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

from TagScriptEngine import Block, Interpreter


class ReactBlock(Block):
    """
    The react block will react with up to 5 emoji to the tag response message.
    The given emoji can be custom or unicode emoji. Emojis can be split with ",".

    **Usage:** ``{react(<emoji,emoji>)}``

    **Payload:** None

    **Parameter:** emoji

    **Examples:** ::

        {react(🅱️)}
        {react(🍎,🍏)}
        {react(<:kappa:754146174843355146>)}
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

    **Usage:** ``{reactu(<emoji,emoji>)}``

    **Payload:** None

    **Parameter:** emoji

    **Examples:** ::

        {react(🅱️)}
        {react(🍎,🍏)}
        {react(<:kappa:754146174843355146>)}
    """

    def will_accept(self, ctx: Interpreter.Context) -> bool:
        dec = ctx.verb.declaration.lower()
        return dec == "reactu"

    def process(self, ctx: Interpreter.Context) -> Optional[str]:
        if not ctx.verb.parameter:
            return None
        ctx.response.actions["reactu"] = [arg.strip() for arg in ctx.verb.parameter.split(",")[:5]]
        return ""
