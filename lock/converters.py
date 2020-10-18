import re
from typing import Union, Optional

import discord
import unidecode
from discord.ext.commands.converter import RoleConverter
from redbot.core import commands
from redbot.core.commands import BadArgument
from redbot.core.utils.chat_formatting import inline

class ChannelToggle:
    async def convert(self, ctx: commands.Context, arg: str) -> Union[bool, None]:
        arg = arg.lower()
        if arg not in ["true", "default", "nuetral"]:
            raise BadArgument(
                f"`{arg} is not a valid channel state. You use provide `true` or `default`."
            )
        if arg == "neutral" or arg == "default":
            ret = None
        elif arg == "true":
            ret = True
        return ret


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

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        try:
            basic_role = await super().convert(ctx, argument)
        except BadArgument:
            pass
        else:
            return basic_role
        guild = ctx.guild
        result = []
        raw_arg = argument.lower().replace(" ", "")
        if guild:
            for r in guild.roles:
                if raw_arg in unidecode.unidecode(r.name.lower().replace(" ", "")):
                    result.append(r)

        if not result:
            raise BadArgument('Role "{}" not found.'.format(argument))

        calculated_result = [
            (role, (len(argument) / len(role.name.replace(" ", ""))) * 100) for role in result
        ]
        sorted_result = sorted(calculated_result, key=lambda r: r[1], reverse=True)
        return sorted_result[0][0]
