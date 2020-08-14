import discord
import aiohttp
import asyncio

from redbot.core import commands, checks, Config


class AltDentifier(commands.Cog):
    """
    Check new users with AltDentifier API
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=60124753086205362,
            force_registration=True,
        )

    @checks.mod_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.command()
    async def altcheck(self, ctx, *, member: discord.Member = None):
        """Check a user on AltDentifier."""

        if not member:
            member = ctx.author
        if member.bot:
            return await ctx.send("Bots can't really be alts you know..")
        e = await self.alt_request(member)
            
        await ctx.send(embed=e)

    async def alt_request(self, member: discord.Member):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://altdentifier.com/api/v2/user/{member.id}/trustfactor") as response:
                response = await response.json()
        color = await self.pick_color(response["trustfactor"])
        e = discord.Embed(
            color=color,
            title="AltDentifier Check",
            description=f"{member.mention} is {response['formatted_trustfactor']}\nTrust Factor: {response['trustfactor']}"
        )
        e.set_thumbnail(url=member.avatar_url)
        return e

    async def pick_color(self, trustfactor: int):
        if trustfactor == 0:
            color = discord.Color.dark_red()
        elif trustfactor == 1:
            color = discord.Color.red()
        elif trustfactor == 2:
            color = discord.Color.green()
        elif trustfactor == 3:
            color = discord.Color.dark_green()
        return color