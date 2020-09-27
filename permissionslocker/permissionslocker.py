# original invoke hook logic from https://github.com/mikeshardmind/SinbadCogs/tree/v3/noadmin
from typing import Literal

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import box

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

async def before_invoke_hook(ctx: commands.Context):
    if not ctx.guild:
        return
    guild = ctx.guild
    if guild.me == guild.owner:
        return
    if await ctx.bot.is_owner(ctx.author):
        return
    data = await ctx.bot.get_cog("PermissionsLocker").config.all()
    if guild.id in data["whitelisted"]:
        return
    author, me = ctx.author, guild.me
    assert isinstance(author, discord.Member)  # nosec

    requiredPerms = discord.Permissions(data["permissions"])
    myPerms = ctx.channel.permissions_for(me)
    if not myPerms.is_superset(requiredPerms):
        missingPerms = await ctx.bot.get_cog("PermissionsLocker").humanize_perms(
            discord.Permissions((myPerms.value ^ requiredPerms.value) & requiredPerms.value),
            True,
        )
        await ctx.send(
            "Hello there!\nI'm missing the following permissions. Without these permissions, I cannot function properly. "
            "Please check your guild and channel permissions to ensure I have these permissions:"
            f"\n{box(missingPerms, 'diff')}",
            delete_after=60,
        )
        raise commands.CheckFailure()


class PermissionsLocker(commands.Cog):
    """
    Force permissions for the bot.
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=4235969345783789456,
            force_registration=True,
        )
        default_global = {"permissions": 387136, "whitelisted": []}
        self.config.register_global(**default_global)

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        return

    @commands.is_owner()
    @commands.group()
    async def permlock(self, ctx):
        """Permissions locker group command."""
        if not ctx.subcommand_passed:
            data = await self.config.all()
            e = discord.Embed(color=await ctx.embed_color(), title="PermissionsLocker")
            e.add_field(
                name="Required Permissions",
                value=str(data["permissions"])
                + box(
                    await self.humanize_perms(discord.Permissions(data["permissions"]), True),
                    "diff",
                ),
                inline=False,
            )
            if data["whitelisted"]:
                whitelisted = []
                for item in data["whitelisted"]:
                    whitelisted.append(str(item))
                e.add_field(name="Whitelisted", value=", ".join(whitelisted), inline=False)
            await ctx.send(embed=e)

    @permlock.command()
    async def perms(self, ctx, permissions: int):
        """Set the permissions value that is required for the bot to work."""
        permissions = discord.Permissions(permissions)
        await self.config.permissions.set(permissions.value)
        await ctx.send(
            f"I will now require these permissions on commands:\n{box(await self.humanize_perms(permissions, True), 'diff')}"
        )

    @permlock.command(aliases=["wl"])
    async def whitelist(self, ctx, guild: int):
        """Whitelist a guild from permission checks."""
        async with self.config.whitelisted() as w:
            w.append(guild)
        await ctx.tick()

    @permlock.command(aliases=["unwl"])
    async def unwhitelist(self, ctx, guild: int):
        """Remove a guild from the whitelist."""
        async with self.config.whitelisted() as w:
            try:
                index = w.index(guild)
            except ValueError:
                return await ctx.send("This is not a guild in the whitelist")
            w.pop(index)
        await ctx.tick()

    async def humanize_perms(self, permissions: discord.Permissions, check: bool):
        perms = dict(iter(permissions))
        perms_list = []
        for key, value in perms.items():
            if value == check:
                perms_list.append(f"+ {key}")
        return "\n".join(perms_list)
