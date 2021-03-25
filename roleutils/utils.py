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

from typing import Tuple, List, Optional
import re

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_list


async def is_allowed_by_hierarchy(bot: Red, mod: discord.Member, member: discord.Member) -> bool:
    return (
        mod.guild.owner_id == mod.id or mod.top_role >= member.top_role or await bot.is_owner(mod)
    )


async def is_allowed_by_role_hierarchy(
    bot: Red,
    bot_me: discord.Member,
    mod: discord.Member,
    role: discord.Role,
) -> Tuple[bool, str]:
    if role >= bot_me.top_role and bot_me.id != mod.guild.owner_id:
        return (False, f"I am not higher than `{role}` in hierarchy.")
    else:
        return (
            (mod.top_role > role) or mod.id == mod.guild.owner_id or await bot.is_owner(mod),
            f"You are not higher than `{role}` in hierarchy.",
        )


def my_role_heirarchy(guild: discord.Guild, role: discord.Role) -> bool:
    return guild.me.top_role > role


MENTION_RE = re.compile(r"@(everyone|here|&[0-9]{17,21})")


def escape_mentions(text: str):
    return MENTION_RE.sub("@\u200b\\1", text)


def humanize_roles(
    roles: List[discord.Role], *, mention: bool = False, bold: bool = True
) -> Optional[str]:
    if not roles:
        return None
    role_strings = []
    for role in roles:
        role_name = escape_mentions(role.name)
        if mention:
            role_strings.append(role.mention)
        elif bold:
            role_strings.append(f"**{role_name}**")
        else:
            role_strings.append(role_name)
    return humanize_list(role_strings)


humanize_members = humanize_roles


async def can_run_command(ctx: commands.Context, command: str) -> bool:
    try:
        result = await ctx.bot.get_command(command).can_run(ctx, check_all_parents=True)
    except commands.CommandError:
        result = False
    return result


async def delete_quietly(message: discord.Message):
    if message.channel.permissions_for(message.guild.me).manage_messages:
        try:
            await message.delete()
        except discord.HTTPException:
            pass


def guild_roughly_chunked(guild: discord.Guild) -> bool:
    return len(guild.members) / guild.member_count > 0.9
