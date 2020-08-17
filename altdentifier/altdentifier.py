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
        self.session = aiohttp.ClientSession()
        self.config = Config.get_conf(
            self,
            identifier=60124753086205362,
            force_registration=True,
        )
        default_guild = {
            "channel": None
        }

        self.config.register_guild(**default_guild)

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

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

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group()
    async def altset(self, ctx):
        """AltDentifier Settings"""

        if not ctx.subcommand_passed:
            data = await self.config.guild(ctx.guild).all()
            description = []

            if data["channel"]:
                channel = f"<#{data['tradeChannel']}>"
            else:
                channel = "None"
            
            description.append(f"AltDentifier Check Channel: {channel}")
            description = "\n".join(description)

            color = await self.bot.get_embed_colour(ctx)
            e = discord.Embed(
                color=color,
                title=f"AltDentifier Settings",
                description=description
            )
            e.set_author(name=ctx.guild, icon_url=ctx.guild.icon_url)
            await ctx.send(embed=e)

    @altset.command()
    async def channel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel to send AltDentifier join checks to.

        This also works as a toggle, so if no channel is provided, it will disable reminders for this server."""

        if not channel:
            await self.config.guild(ctx.guild).channel.clear()
            await ctx.send("Disabled AltDentifier join checks in this server.")
        else:
            try:
                await channel.send("Set this channel as the message channel for AltDentifier join checks")
                await self.config.guild(ctx.guild).channel.set(channel.id)
            except discord.errors.Forbidden:
                await ctx.send("I do not have permission to talk in that channel.")
        await ctx.tick()

    async def alt_request(self, member: discord.Member):
        async with self.session.get(f"https://altdentifier.com/api/v2/user/{member.id}/trustfactor") as response:
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

    @commands.Cog.listener()
    async def on_member_join(self, member):
        data = await self.config.guild(member.guild).all()
        if not data["channel"]:
            return
        channel = member.guild.get_channel(data["channel"])
        if not channel:
            await self.config.guild(member.guild).channel.clear()
            return
        e = await self.alt_request(member)
        await channel.send(embed=e)