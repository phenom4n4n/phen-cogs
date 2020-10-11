import discord
from redbot.core.utils.chat_formatting import humanize_list


async def is_allowed_by_hierarchy(bot, mod: discord.Member, member: discord.Member):
    return mod.top_role.position > member.top_role.position or await bot.is_owner(mod)


def is_allowed_by_role_hierarchy(
    bot,
    bot_me: discord.Member,
    mod: discord.Member,
    role: discord.Role,
):
    if role.position >= bot_me.top_role.position:
        return (False, f"I am not higher than `{role}` in hierarchy.")
    else:
        return (
            (mod.top_role.position > role.position) or mod == mod.guild.owner,
            f"You are not higher than `{role}` in hierarchy.",
        )


def humanize_roles(roles: list) -> str:
    return humanize_list([f"`{role.name}`" for role in roles])
