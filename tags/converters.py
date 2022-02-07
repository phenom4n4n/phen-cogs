"""
MIT License

Copyright (c) 2020-present phenom4n4n

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

from .errors import TagError
from .objects import Tag

PASTEBIN_RE = re.compile(r"(?:https?://(?:www\.)?)?pastebin\.com/(?:raw/)?([a-zA-Z0-9]+)")


class TagSearcher:
    def __init__(self, **search_kwargs):
        self.search_kwargs = search_kwargs

    def get_tag(self, ctx: commands.Context, argument: str):
        return ctx.cog.get_tag(ctx.guild, argument, **self.search_kwargs)


class TagName(TagSearcher, commands.Converter):
    def __init__(self, *, allow_named_tags: bool = False, **kwargs):
        self.allow_named_tags = allow_named_tags
        super().__init__(**kwargs)

    async def convert(self, ctx: commands.Context, argument: str) -> str:
        command = ctx.bot.get_command(argument)
        if command:
            raise commands.BadArgument(f"`{argument}` is already a registered command.")

        if not self.allow_named_tags:
            tag = self.get_tag(ctx, argument)
            if tag:
                raise commands.BadArgument(f"`{argument}` is already a registered tag or alias.")

        return "".join(argument.split())


class TagConverter(TagSearcher, commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> Tag:
        if not ctx.guild and not await ctx.bot.is_owner(ctx.author):
            raise commands.BadArgument("Tags can only be used in guilds.")

        tag = self.get_tag(ctx, argument)
        if tag:
            return tag
        else:
            raise commands.BadArgument(f'Tag "{escape_mentions(argument)}" not found.')


GlobalTagConverter = TagConverter(check_global=True, global_priority=True)
GuildTagConverter = TagConverter(check_global=False, global_priority=False)


class TagScriptConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        try:
            await ctx.cog.validate_tagscript(ctx, argument)
        except TagError as e:
            raise commands.BadArgument(str(e))
        return argument


class PastebinConverter(TagScriptConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        match = PASTEBIN_RE.match(argument)
        if not match:
            raise commands.BadArgument(f"`{argument}` is not a valid Pastebin link.")
        paste_id = match.group(1)
        async with ctx.cog.session.get(f"https://pastebin.com/raw/{paste_id}") as resp:
            if resp.status != 200:
                raise commands.BadArgument(f"`{argument}` is not a valid Pastebin link.")
            tagscript = await resp.text()
        return await super().convert(ctx, tagscript)
