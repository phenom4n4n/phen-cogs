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

from typing import Tuple, Union, List
import discord
from unidecode import unidecode
from redbot.core import commands
from rapidfuzz import process
from redbot.core.commands import (
    BadArgument,
    Converter,
    MemberConverter,
    RoleConverter,
    EmojiConverter,
    IDConverter,
)
from redbot.core.utils.chat_formatting import inline

from .utils import is_allowed_by_hierarchy, is_allowed_by_role_hierarchy


# original converter from https://github.com/TrustyJAID/Trusty-cogs/blob/master/serverstats/converters.py#L19
class FuzzyRole(RoleConverter):
    """
    This will accept role ID's, mentions, and perform a fuzzy search for
    roles within the guild and return a list of role objects
    matching partial names

    Guidance code on how to do this from:
    https://github.com/Rapptz/discord.py/blob/rewrite/discord/ext/commands/converter.py#L85
    https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/mod/mod.py#L24
    """

    def __init__(self, response: bool = True):
        self.response = response
        super().__init__()

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        try:
            basic_role = await super().convert(ctx, argument)
        except BadArgument:
            pass
        else:
            return basic_role
        guild = ctx.guild
        result = [(r[2], r[1]) for r in process.extract(
            argument,
            {r: unidecode(r.name) for r in guild.roles},
            limit=None,
            score_cutoff=75,
        )]
        if not result:
            raise BadArgument(f'Role "{argument}" not found.' if self.response else None)

        sorted_result = sorted(result, key=lambda r: r[1], reverse=True)
        return sorted_result[0][0]


class StrictRole(FuzzyRole):
    def __init__(self, response: bool = True, *, check_integrated: bool = True):
        self.response = response
        self.check_integrated = check_integrated
        super().__init__(response)

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        role = await super().convert(ctx, argument)
        if self.check_integrated and role.managed:
            raise BadArgument(
                f"`{role}` is an integrated role and cannot be assigned."
                if self.response
                else None
            )
        allowed, message = await is_allowed_by_role_hierarchy(ctx.bot, ctx.me, ctx.author, role)
        if not allowed:
            raise BadArgument(message if self.response else None)
        return role


class TouchableMember(MemberConverter):
    def __init__(self, response: bool = True):
        self.response = response
        super().__init__()

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Member:
        member = await super().convert(ctx, argument)
        if not await is_allowed_by_hierarchy(ctx.bot, ctx.author, member):
            raise BadArgument(
                f"You cannot do that since you aren't higher than {member} in hierarchy."
                if self.response
                else None
            )
        else:
            return member


class RealEmojiConverter(EmojiConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> Union[discord.Emoji, str]:
        try:
            emoji = await super().convert(ctx, argument)
        except BadArgument:
            try:
                await ctx.message.add_reaction(argument)
            except discord.HTTPException:
                raise commands.EmojiNotFound(argument)
            else:
                emoji = argument
        return emoji


class EmojiRole(StrictRole, RealEmojiConverter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> Tuple[Union[discord.Emoji, str], discord.Role]:
        split = argument.split(";")
        if len(split) < 2:
            raise BadArgument
        emoji = await RealEmojiConverter.convert(self, ctx, split[0])
        role = await StrictRole.convert(self, ctx, split[1])
        return emoji, role


class ObjectConverter(IDConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Object:
        match = self._get_id_match(argument)
        if not match:
            raise BadArgument
        return discord.Object(int(match.group(0)))


class TargeterArgs(Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> List[discord.Member]:
        members = await ctx.bot.get_cog("Targeter").args_to_list(ctx, argument)
        if not members:
            raise BadArgument(
                f"No one was found with the given args.\nCheck out `{ctx.clean_prefix}target help` for an explanation."
            )
        return members
