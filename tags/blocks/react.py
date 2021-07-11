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

from TagScriptEngine import Block, Context


class ReactBlock(Block):
    """
    The react block will react with up to 5 emoji to the tag response message.
    If the name used is ``reactu``, it will react to the tag invocation instead.
    The given emoji can be custom or unicode emoji. Emojis can be split with ",".

    The block accepts emojis being passed to the parameter or the payload, but not both.

    **Usage:** ``{react(<emoji,emoji>):[emoji,emoji]}``

    **Aliases:** ``reactu``

    **Payload:** emoji

    **Parameter:** emoji

    **Examples:** ::

        {react(🅱️)}
        {react(🍎,🍏)}
        {react(<:kappa:754146174843355146>)}
        {reactu:🅱️}
    """

    ACCEPTED_NAMES = ("react", "reactu")

    def will_accept(self, ctx: Context) -> bool:
        if not (ctx.verb.parameter or ctx.verb.payload):
            return False
        return super().will_accept(ctx)

    def process(self, ctx: Context) -> Optional[str]:
        emojis = ctx.verb.parameter or ctx.verb.payload
        ctx.response.actions[ctx.verb.declaration.lower()] = [
            arg.strip() for arg in emojis.split(",")[:5]
        ]
        return ""
