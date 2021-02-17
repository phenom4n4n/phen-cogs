from typing import Tuple
import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_list


async def is_allowed_by_hierarchy(bot: Red, mod: discord.Member, member: discord.Member) -> bool:
    return mod.top_role >= member.top_role or await bot.is_owner(mod)


async def is_allowed_by_role_hierarchy(
    bot: Red,
    bot_me: discord.Member,
    mod: discord.Member,
    role: discord.Role,
) -> Tuple[bool, str]:
    if role >= bot_me.top_role and not bot_me.id == mod.guild.owner_id:
        return (False, f"I am not higher than `{role}` in hierarchy.")
    else:
        return (
            (mod.top_role > role) or mod.id == mod.guild.owner_id or await bot.is_owner(mod),
            f"You are not higher than `{role}` in hierarchy.",
        )


def my_role_heirarchy(guild: discord.Guild, role: discord.Role) -> bool:
    return guild.me.top_role > role


def humanize_roles(roles: list) -> str:
    return humanize_list([f"`{role.name}`" for role in roles])


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
