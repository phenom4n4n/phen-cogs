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
        default_global = {

        }
        default_guild = {

        }
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

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

    @embed.command(aliases=["fromjson"])
    async def fromdata(self, ctx, *, data):
        """Make an embed from valid JSON.

        This must be in the format expected by [this Discord documenation](https://discord.com/developers/docs/resources/channel#embed-object "Click me!").
        Here's [a json example](https://gist.github.com/TwinDragon/9cf12da39f6b2888c8d71865eb7eb6a8 "Click me!").
        Note: timestamps in embeds currently aren't supported."""
        await self.str_embed_converter(ctx, data)
        await ctx.tick()

    @embed.command(aliases=["fromjsonfile"])
    async def fromdatafile(self, ctx):
        """Make an embed from a valid JSON file.

        This must be in the format expected by [this Discord documenation](https://discord.com/developers/docs/resources/channel#embed-object "Click me!").
        Here's [a json example](https://gist.github.com/TwinDragon/9cf12da39f6b2888c8d71865eb7eb6a8 "Click me!").
        Note: timestamps in embeds currently aren't supported."""
        if not ctx.message.attachments:
            return await ctx.send("You need to provide a file for this..")
        attachment = ctx.message.attachments[0]
        content = await attachment.read()
        try:
            data = content.decode("utf-8")
        except UnicodeDecodeError:
            return await ctx.send("Invalid file")
        await self.str_embed_converter(ctx, data)
        await ctx.tick()

    @embed.command()
    async def download(self, ctx, message: discord.Message, index: int = 0):
        """Download a JSON file for a message's embed.

        If the message has multiple embeds, you can pass a number to `index` to specify which embed."""
        embed = message.embeds[0]
        data = embed.to_dict()
        data = json.dumps(data, indent=4)
        if len(data) <= 1990:
            await ctx.send(f"```\n{data}\n```")

    async def str_embed_converter(self, ctx, data):
        data.replace("'", '"')
        try:
            data = json.loads(data)
        except json.decoder.JSONDecodeError as error:
            return await self.embed_convert_error(ctx, "JSON Parse Error", error)
        try:
            e = discord.Embed.from_dict(data)
        except Exception as error:
            return await self.embed_convert_error(ctx, "Embed Parse Error", error)
        try:
            await ctx.send(embed=e)
        except discord.errors.HTTPException as error:
            return await self.embed_convert_error(ctx, "Embed Send Error", error)

    async def embed_convert_error(self, ctx, errorType, error):
        embed = discord.Embed(
            color=await self.bot.get_embed_color(ctx),
            title=errorType,
            description=f"```py\n{error}\n```"
        )
        embed.set_footer(text=f"Use `{ctx.prefix}help {ctx.command.qualified_name}` to see an example")
        await ctx.send(embed=embed)