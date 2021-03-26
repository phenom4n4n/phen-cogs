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

from discord.utils import escape_mentions
from redbot.core import commands

from .errors import MissingTagPermissions
from .objects import SlashTag

SLASH_NAME = re.compile(r"^{?([\w-]{1,32})}?$")


class TagName(commands.Converter):
    def __init__(self, *, check_command: bool = False):
        self.check_command = check_command

    async def convert(self, ctx: commands.Converter, argument: str) -> str:
        if self.check_command:
            # TODO check if tag name is already registered to this guild
            ...
        if len(argument) > 32:
            raise commands.BadArgument("Slash command names may not exceed 32 characters.")
        match = SLASH_NAME.match(argument)
        if not match:
            raise commands.BadArgument(
                "Slash command characters must be alphanumeric or '_' or '-'."
            )
        return match.group(1)


class TagConverter(commands.Converter):
    def __init__(self, *, check_global: bool = False, global_priority: bool = False):
        self.check_global = check_global
        self.global_priority = global_priority

    async def convert(self, ctx: commands.Context, argument: str) -> SlashTag:
        cog = ctx.bot.get_cog("SlashTags")
        tag = cog.get_tag_by_name(
            ctx.guild,
            argument,
        )
        if tag:
            return tag
        else:
            raise commands.BadArgument(f'Tag "{escape_mentions(argument)}" not found.')


class TagScriptConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        cog = ctx.bot.get_cog("SlashTags")
        try:
            await cog.validate_tagscript(ctx, argument)
        except MissingTagPermissions as e:
            raise commands.BadArgument(str(e))
        return argument
