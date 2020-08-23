import discord
import aiohttp
import typing
import json

from redbot.core import commands, checks, Config

class EmbedGenerator(commands.Cog):
    """
    Create, post, and store embeds.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=43248937299564234735284,
            force_registration=True,
        )

    @checks.bot_has_permissions(embed_links=True)
    @commands.group()
    async def embed(self, ctx):
        """Manage embeds."""

    @embed.command()
    async def simple(self, ctx, color: typing.Optional[discord.Color], title: str, *, description: str):
        """Make a simple embed.

        Put the title in quotes if it is multiple words."""
        if not color:
            color = await self.bot.get_embed_color(ctx)
        e = discord.Embed(
            color=color,
            title=title,
            description=description
        )
        await ctx.send(embed=e)

    @embed.command()
    async def fromdata(self, ctx, *, data):
        """Make an embed from valid JSON/YAML.

        This must be in the format expected by [this Discord documenation](https://discord.com/developers/docs/resources/channel#embed-object "Click me!").
        Here's an [embed generator](https://discohook.org/?message=eyJtZXNzYWdlIjp7ImVtYmVkcyI6W3t9XX19 "Click me!")."""
        try:
            data = json.loads(data)
        except json.decoder.JSONDecodeError:
            return await ctx.send("Invalid Data")
        e = discord.Embed.from_dict(data)
        await ctx.send(embed=e)