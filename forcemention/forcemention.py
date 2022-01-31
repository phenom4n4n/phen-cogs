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

# this is a modified version of Bobloy's forcemention cog
import asyncio

import discord
from redbot.core import checks, commands
from redbot.core.bot import Red


class ForceMention(commands.Cog):
    """
    Mention the unmentionables
    """

    __version__ = "1.0.0"

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
