import re
import discord
import unidecode

from typing import List, Union

from redbot.core import commands

from discord.ext.commands.converter import IDConverter, _get_from_guilds

from redbot.core.commands import BadArgument
from redbot.core.utils.chat_formatting import inline

# original converter from https://github.com/TrustyJAID/Trusty-cogs/blob/master/serverstats/converters.py#L19
class FuzzyRole(IDConverter):
    """
    This will accept role ID's, mentions, and perform a fuzzy search for
    roles within the guild and return a list of role objects
    matching partial names

    Guidance code on how to do this from:
    https://github.com/Rapptz/discord.py/blob/rewrite/discord/ext/commands/converter.py#L85
    https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/mod/mod.py#L24
    """

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        bot = ctx.bot
        match = self._get_id_match(argument) or re.match(r"<@&([0-9]+)>$", argument)
        guild = ctx.guild
        result = []
        if match is None:
            # Not a mention
            if guild:
                for r in guild.roles:
                    if argument.lower() in unidecode.unidecode(r.name.lower().replace(" ", "")):
                        result.append(r)
                        continue
        else:
            role_id = int(match.group(1))
            if guild:
                result.append(guild.get_role(role_id))
            else:
                result.append(_get_from_guilds(bot, "get_role", role_id))

        if not result:
            raise BadArgument('Role "{}" not found'.format(argument))

        calculated_result = [(role, (len(argument) / len(role.name.replace(" ", ""))) * 100) for role in result]
        sorted_result = sorted(calculated_result, key=lambda r: r[1], reverse=True)
        return sorted_result[0][0]