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
from typing import TYPE_CHECKING

from discord.utils import escape_mentions
from redbot.core import commands

from .errors import MissingTagPermissions
from .objects import SlashTag

SLASH_NAME = re.compile(r"^{?([\w-]{1,32})}?$")


class TagSearcher:
    def __init__(self, **search_kwargs):
        self.search_kwargs = search_kwargs

    def get_tag(self, ctx: commands.Context, argument: str):
        cog = ctx.bot.get_cog("SlashTags")
        return cog.get_tag_by_name(ctx.guild, argument, **self.search_kwargs)


class TagName(TagSearcher, commands.Converter):
    def __init__(self, *, check_command: bool = True, **search_kwargs):
        self.check_command = check_command
        super().__init__(**search_kwargs)

    async def convert(self, ctx: commands.Converter, argument: str) -> str:
        if len(argument) > 32:
            raise commands.BadArgument("Slash tag names may not exceed 32 characters.")
        match = SLASH_NAME.match(argument)
        if not match:
            raise commands.BadArgument("Slash tag characters must be alphanumeric or '_' or '-'.")
        name = match.group(1)
        if self.check_command:
            if self.get_tag(ctx, name):
                raise commands.BadArgument(
                    f"A slash tag named `{name}` is already registered."
                )
        return name


class TagConverter(TagSearcher, commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> SlashTag:
        cog = ctx.bot.get_cog("SlashTags")
        tag = self.get_tag(ctx, argument)
        if not tag:
            raise commands.BadArgument(f'Tag "{escape_mentions(argument)}" not found.')
        return tag


GlobalTagConverter = TagConverter(check_global=True, global_priority=True)
GuildTagConverter = TagConverter(check_global=False, global_priority=False)


class TagScriptConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        cog = ctx.bot.get_cog("SlashTags")
        try:
            await cog.validate_tagscript(ctx, argument)
        except MissingTagPermissions as e:
            raise commands.BadArgument(str(e))
        return argument


if TYPE_CHECKING:
    TagConverter = SlashTag
    TagScriptConverter = str
