# this is a modified version of Bobloy's forcemention cog
import discord

from redbot.core import checks, commands

from redbot.core.bot import Red
import typing
import asyncio

class ForceMention(commands.Cog):
    """
    Mention the unmentionables
    """

    def __init__(self, bot: Red):
        self.bot = bot

    async def red_delete_data_for_user(self, **kwargs):
        return
        
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
        try:
            await ctx.message.delete()
        except:
            pass
        await self.forcemention(ctx.channel, role, message)

    async def forcemention(self, channel: discord.TextChannel, role: discord.Role, message: str, embed: typing.Optional[discord.Embed] = None):
        mentionPerms = discord.AllowedMentions(roles=True)
        if role.mentionable:
            await channel.send(message, allowed_mentions=mentionPerms, embed=embed if embed else None)
        elif channel.permissions_for(channel.guild.me).mention_everyone:
            await channel.send(message, allowed_mentions=mentionPerms, embed=embed if embed else None)
        elif channel.permissions_for(channel.guild.me).manage_roles:
            await role.edit(mentionable=True)
            await channel.send(message, allowed_mentions=mentionPerms, embed=embed if embed else None)
            await asyncio.sleep(5)
            await role.edit(mentionable=False)
        else:
            await channel.send(message, allowed_mentions=mentionPerms, embed=embed if embed else None)