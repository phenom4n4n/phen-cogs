from typing import Union, Optional

import discord
from unidecode import unidecode
from rapidfuzz import process
from discord.ext.commands.converter import Converter, RoleConverter, TextChannelConverter
from redbot.core import commands
from redbot.core.commands import BadArgument
from redbot.core.utils.chat_formatting import inline


class ChannelToggle(Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> Union[bool, None]:
        arg = arg.lower()
        if arg not in ["true", "default", "neutral"]:
            raise BadArgument(
                f"`{arg} is not a valid channel state. You use provide `true` or `default`."
            )
        if arg == "neutral" or arg == "default":
            ret = None
        elif arg == "true":
            ret = True
        return ret


class LockableChannel(TextChannelConverter):
    async def convert(self, ctx: commands.Context, arg: str) -> Optional[discord.TextChannel]:
        channel = await super().convert(ctx, arg)
        if not ctx.channel.permissions_for(ctx.me).manage_roles:
            raise BadArgument(
                f"I do not have permission to edit permissions in {channel.mention}."
            )
        return channel


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
        result = []
        for r in process.extract(
            argument,
            {r: unidecode(r.name) for r in guild.roles},
            limit=None,
            score_cutoff=75,
        ):
            result.append((r[2], r[1]))

        if not result:
            raise BadArgument(f'Role "{argument}" not found.' if self.response else None)

        sorted_result = sorted(result, key=lambda r: r[1], reverse=True)
        return sorted_result[0][0]
