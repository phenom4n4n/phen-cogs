# this is a modified version of Bobloy's forcemention cog
import discord

from redbot.core import Config, checks, commands

from redbot.core.bot import Red
from typing import Any
import asyncio

Cog: Any = getattr(commands, "Cog", object)

class ForceMention(Cog):
    """
    Mention the unmentionables
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9811198108111121, force_registration=True)
        default_global = {}
        default_guild = {}

        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    @checks.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_roles=True)
    @commands.command(name="forcemention")
    async def cmd_forcemention(self, ctx: commands.Context, role: discord.Role, *, message: str = None):
        """
       Mentions that role, regardless if it's unmentionable. 

       Will automatically delete the command invocation.
       """
        if message:
            message = f"{role.mention}\n{message}"
        else:
            message = role.mention
        await ctx.message.delete()
        await self.forcemention(ctx.channel, role, message)

    async def forcemention(self, channel: discord.Channel, role: discord.Role, message: str):
        mentionPerms = discord.AllowedMentions(roles=True)
        if role.mentionable:
            await channel.send(message, allowed_mentions=mentionPerms)
        elif channel.permissions_for(channel.guild.me).mention_everyone:
            await channel.send(message, allowed_mentions=mentionPerms)
        elif channel.permissions_for(channel.guild.me).manage_roles:
            await role.edit(mentionable=True)
            await channel.send(message, allowed_mentions=mentionPerms)
            await asyncio.sleep(5)
            await role.edit(mentionable=False)
        else:
            await channel.send(message, allowed_mentions=mentionPerms)