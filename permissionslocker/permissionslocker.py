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

# original invoke hook logic from https://github.com/mikeshardmind/SinbadCogs/tree/v3/noadmin
from typing import Literal, Optional, Set

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import box

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class PermissionsLocker(commands.Cog):
    """
    Force permissions for the bot.
    """

    __version__ = "1.3.0"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\nCog Version: {self.__version__}"

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=4235969345783789456,
            force_registration=True,
        )
        default_global = {"permissions": 387136, "whitelisted": []}
        self.config.register_global(**default_global)
        self.perms: Optional[discord.Permissions] = None
        self._whitelist: Set[int] = set()

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        return

    async def initialize(self):
        data = await self.config.all()
        self.perms = discord.Permissions(data["permissions"])
        self._whitelist.update(data["whitelisted"])
        self.bot.before_invoke(self.before_invoke_hook)

    def cog_unload(self):
        self.bot.remove_before_invoke_hook(self.before_invoke_hook)

    async def before_invoke_hook(self, ctx: commands.Context):
        if not ctx.guild or isinstance(ctx.command, commands.commands._AlwaysAvailableCommand):
            return
        guild = ctx.guild
        if guild.id in self._whitelist:
            return
        me = guild.me
        if me == guild.owner:
            return
        if await ctx.bot.is_owner(ctx.author):
            return

        required_perms = self.perms
        myPerms = ctx.channel.permissions_for(me)
        if not myPerms.is_superset(required_perms):
            missingPerms = self.humanize_perms(
                discord.Permissions((myPerms.value ^ required_perms.value) & required_perms.value),
                True,
            )
            await ctx.send(
                "Hello there!\nI'm missing the following permissions. Without these permissions, I cannot function properly. "
                "Please check your guild and channel permissions to ensure I have these permissions:"
                f"\n{box(missingPerms, 'diff')}",
                delete_after=60,
            )
            raise commands.CheckFailure()

    @commands.is_owner()
    @commands.group()
    async def permlock(self, ctx):
        """Permissions locker group command."""

    @permlock.command()
    async def perms(self, ctx, permissions: int):
        """Set the permissions value that is required for the bot to work."""
        permissions = discord.Permissions(permissions)
        await self.config.permissions.set(permissions.value)
        await ctx.send(
            f"I will now require these permissions on commands:\n{box(self.humanize_perms(permissions, True), 'diff')}"
        )
        self.perms = permissions

    @permlock.command(aliases=["wl"])
    async def whitelist(self, ctx, guild: int):
        """Whitelist a guild from permission checks."""
        async with self.config.whitelisted() as w:
            w.append(guild)
        self._whitelist.add(guild)
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
        self._whitelist.remove(guild)
        await ctx.tick()

    @commands.bot_has_permissions(embed_links=True)
    @permlock.command()
    async def settings(self, ctx: commands.Context):
        """View PermissionsLocker settings."""
        data = await self.config.all()
        e = discord.Embed(color=await ctx.embed_color(), title="PermissionsLocker")
        e.add_field(
            name="Required Permissions",
            value=str(data["permissions"])
            + box(
                self.humanize_perms(discord.Permissions(data["permissions"]), True),
                "diff",
            ),
            inline=False,
        )
        if data["whitelisted"]:
            whitelisted = [str(item) for item in data["whitelisted"]]
            e.add_field(name="Whitelisted", value=", ".join(whitelisted), inline=False)
        await ctx.send(embed=e)

    def humanize_perms(self, permissions: discord.Permissions, check: bool):
        perms = dict(permissions)
        perms_list = [f"+ {key}" for key, value in perms.items() if value == check]
        return "\n".join(perms_list)
