import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_list


async def is_allowed_by_hierarchy(bot: Red, mod: discord.Member, member: discord.Member):
    return mod.top_role.position >= member.top_role.position or await bot.is_owner(mod)


def is_allowed_by_role_hierarchy(
    bot: Red,
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


async def can_run_command(ctx: commands.Context, command: str) -> bool:
    try:
        result = await ctx.bot.get_command(command).can_run(ctx, check_all_parents=True)
    except commands.CommandError:
        result = False
    return result
