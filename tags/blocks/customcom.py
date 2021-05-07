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

import re

from TagScriptEngine import Block, Context

CONVERTER_RE = re.compile(r"(?i)(\d{1,2})(?:\.[a-z]+)?(?::[a-z]+)?")


class ContextVariableBlock(Block):
    def will_accept(self, ctx: Context) -> bool:
        dec = ctx.verb.declaration.lower().split(".", 1)[0]
        return dec in ("author", "channel", "server", "guild")

    def process(self, ctx: Context) -> str:
        dec = ctx.verb.declaration.lower().split(".", 1)
        parameter = f"({dec[1]})" if len(dec) == 2 else ""
        return "{%s%s}" % (dec[0], parameter)


class ConverterBlock(Block):
    def will_accept(self, ctx: Context) -> bool:
        return bool(CONVERTER_RE.match(ctx.verb.declaration))

    def process(self, ctx: Context) -> str:
        match = CONVERTER_RE.match(ctx.verb.declaration)
        num = match.group(1)
        return "{args(%s)}" % num
