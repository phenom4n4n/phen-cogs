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

import discord
from discord.ext.commands.converter import Converter, RoleConverter
from rapidfuzz import process
from redbot.core import commands
from redbot.core.commands import BadArgument
from unidecode import unidecode


def is_allowed_by_role_hierarchy(
    bot,
    bot_me: discord.Member,
    mod: discord.Member,
    role: discord.Role,
):
    if role >= bot_me.top_role:
        return (False, f"I am not higher than `{role}` in hierarchy.")
    else:
        return (
            (mod.top_role > role) or mod == mod.guild.owner,
            f"You are not higher than `{role}` in hierarchy.",
        )


class LevelConverter(Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        try:
            level = int(argument)
        except ValueError:
            raise BadArgument
        if level not in range(4):
            raise BadArgument(
                "This is not a valid Trust Level. The valid Levels are: 0, 1, 2, and 3."
            )
        else:
            return level


class ActionConverter(Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        if argument.lower() not in ["kick", "ban"]:
            raise BadArgument(
                "This is not a valid action. The valid actions are kick and ban. For roles, supply a role."
            )
        return argument.lower()


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
        result = [
            (r[2], r[1])
            for r in process.extract(
                argument,
                {r: unidecode(r.name) for r in guild.roles},
                limit=None,
                score_cutoff=75,
            )
        ]
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
        allowed, message = is_allowed_by_role_hierarchy(ctx.bot, ctx.me, ctx.author, role)
        if not allowed:
            raise BadArgument(message if self.response else None)
        return role
