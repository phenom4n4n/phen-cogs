# this is a modified version of Bobloy's forcemention cog
import asyncio

import discord
from redbot.core import checks, commands
from redbot.core.bot import Red


class ForceMention(commands.Cog):
    """
    Mention the unmentionables
    """

    def __init__(self, bot: Red):
        self.bot = bot

    async def red_delete_data_for_user(self, **kwargs):
        return

    @checks.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(mention_everyone=True)
    @commands.command(name="forcemention")
    async def cmd_forcemention(
        self, ctx: commands.Context, role: discord.Role, *, message: str = None
    ):
        """
        Mentions that role, regardless if it's unmentionable.

        Will automatically delete the command invocation.
        """
        message = f"{role.mention}\n{message}" if message else role.mention
        try:
            await ctx.message.delete()
        except:
            pass
        await self.forcemention(ctx.channel, role, message)

    async def forcemention(
        self, channel: discord.TextChannel, role: discord.Role, message: str, **kwargs
    ):
        mentionPerms = discord.AllowedMentions(roles=True)
        me = channel.guild.me
        if (
            not role.mentionable
            and not channel.permissions_for(me).mention_everyone
            and channel.permissions_for(me).manage_roles
            and me.top_role > role
        ):
            await role.edit(mentionable=True)
            await channel.send(message, allowed_mentions=mentionPerms, **kwargs)
            await asyncio.sleep(1.5)
            await role.edit(mentionable=False)
        else:
            await channel.send(message, allowed_mentions=mentionPerms, **kwargs)
