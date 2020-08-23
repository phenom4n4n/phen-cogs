import discord
import aiohttp
import typing
import json
import io

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
            "embeds": {}
        }
        default_guild = {
            "embeds": {}
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
        Here's [a json example](https://gist.github.com/TwinDragon/9cf12da39f6b2888c8d71865eb7eb6a8 "Click me!")."""
        await self.str_embed_converter(ctx, data)
        await ctx.tick()

    @embed.command(aliases=["fromjsonfile", "fromdatafile"])
    async def fromfile(self, ctx):
        """Make an embed from a valid JSON file.

        This doesn't actually need to be a `.json` file, but it should follow the format expected by [this Discord documenation](https://discord.com/developers/docs/resources/channel#embed-object "Click me!").
        Here's [a json example](https://gist.github.com/TwinDragon/9cf12da39f6b2888c8d71865eb7eb6a8 "Click me!")."""
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

    @embed.command(name="frommsg", aliases=["frommessage"])
    async def com_frommsg(self, ctx, message: discord.Message, index: int = 0):
        """Post an embed from a message.

        If the message has multiple embeds, you can pass a number to `index` to specify which embed."""
        embed = await self.frommsg(ctx, message, index)
        if not embed:
            return
        await ctx.send(embed=embed)

    @embed.command()
    async def download(self, ctx, message: discord.Message, index: int = 0):
        """Download a JSON file for a message's embed.

        If the message has multiple embeds, you can pass a number to `index` to specify which embed."""
        embed = await self.frommsg(ctx, message, index)
        if not embed:
            return
        data = embed.to_dict()
        data = json.dumps(data, indent=4)
        fp = io.BytesIO(bytes(data, "utf-8"))
        await ctx.send(file=discord.File(fp, "embed.json"))
    
    @embed.command(name="show", aliases=["view", "drop"])
    async def com_drop(self, ctx, name: str):
        """View an embed that is stored on this server."""
        data = await self.config.guild(ctx.guild).embeds()
        try:
            embed = data[name]
        except KeyError:
            await ctx.send("This is not a stored embed.")
            return
        embed = discord.Embed.from_dict(embed)
        await ctx.send(embed=embed)

    @embed.command(aliases=["delete", "rm", "del"])
    async def remove(self, ctx, name):
        """Remove a stored embed on this server."""
        try:
            async with self.config.guild(ctx.guild).embeds() as a:
                del a[name]
            await ctx.send("Embed deleted.")
        except KeyError:
            await ctx.send("This is not a stored embed.")

    @checks.mod_or_permissions(manage_guild=True)
    @embed.group()
    async def store(self, ctx):
        """Store embeds for server use."""
        if not ctx.subcommand_passed:
            embeds = await self.config.guild(ctx.guild).embeds()
            description = []

            for embed in embeds:
                description.append(f"`{embed}`")
            description = "\n".join(description)

            color = await self.bot.get_embed_colour(ctx)
            e = discord.Embed(
                color=color,
                title=f"Stored Embeds",
                description=description
            )
            e.set_author(name=ctx.guild, icon_url=ctx.guild.icon_url)
            await ctx.send(embed=e)

    @store.command(name="simple")
    async def store_simple(self, ctx, name: str, color: typing.Optional[discord.Color], title: str, *, description: str):
        """Store a simple embed on this server.

        Put the title in quotes if it is multiple words."""
        if not color:
            color = await self.bot.get_embed_color(ctx)
        e = discord.Embed(
            color=color,
            title=title,
            description=description
        )
        await ctx.send(embed=e)
        await self.store_embed(ctx, name, e)
        await ctx.tick()

    @store.command(name="fromdata", aliases=["fromjson"])
    async def store_fromdata(self, ctx, name: str, *, data):
        """Store an embed from valid JSON on this server.

        This must be in the format expected by [this Discord documenation](https://discord.com/developers/docs/resources/channel#embed-object "Click me!").
        Here's [a json example](https://gist.github.com/TwinDragon/9cf12da39f6b2888c8d71865eb7eb6a8 "Click me!")."""
        e = await self.str_embed_converter(ctx, data)
        if e:
            await self.store_embed(ctx, name, e)
        await ctx.tick()

    @store.command(name="fromfile", aliases=["fromjsonfile", "fromdatafile"])
    async def store_fromfile(self, ctx, name: str):
        """Store an embed from a valid JSON file on this server.

        This doesn't actually need to be a `.json` file, but it should follow the format expected by [this Discord documenation](https://discord.com/developers/docs/resources/channel#embed-object "Click me!").
        Here's [a json example](https://gist.github.com/TwinDragon/9cf12da39f6b2888c8d71865eb7eb6a8 "Click me!")."""
        if not ctx.message.attachments:
            return await ctx.send("You need to provide a file for this..")
        attachment = ctx.message.attachments[0]
        content = await attachment.read()
        try:
            data = content.decode("utf-8")
        except UnicodeDecodeError:
            return await ctx.send("Invalid file")
        e = await self.str_embed_converter(ctx, data)
        if e:
            await self.store_embed(ctx, name, e)
        await ctx.tick()

    @store.command(name="frommsg", aliases=["frommessage"])
    async def store_frommsg(self, ctx, name: str, message: discord.Message, index: int = 0):
        """Store an embed from a message on this server.

        If the message has multiple embeds, you can pass a number to `index` to specify which embed."""
        embed = await self.frommsg(ctx, message, index)
        if not embed:
            return
        await ctx.send(embed=embed)
        await self.store_embed(ctx, name, embed)

    async def store_embed(self, ctx: commands.Context, name: str, embed: discord.Embed):
        embed = embed.to_dict()
        async with self.config.guild(ctx.guild).embeds() as a:
            a[name] = embed
        await ctx.send(f"Embed stored under the name `{name}`.")

    async def frommsg(self, ctx: commands.Context, message: discord.Message, index: int = 0):
        try:
            embed = message.embeds[index]
            return embed
        except IndexError:
            await ctx.send("This is not a valid embed/index.")
            return

    async def str_embed_converter(self, ctx, data):
        data = data.strip("```")
        try:
            data = json.loads(data)
        except json.decoder.JSONDecodeError as error:
            await self.embed_convert_error(ctx, "JSON Parse Error", error)
            return
        try:
            e = discord.Embed.from_dict(data)
        except Exception as error:
            await self.embed_convert_error(ctx, "Embed Parse Error", error)
            return
        try:
            await ctx.send(embed=e)
            return e
        except discord.errors.HTTPException as error:
            await self.embed_convert_error(ctx, "Embed Send Error", error)
            return

    async def embed_convert_error(self, ctx, errorType, error):
        embed = discord.Embed(
            color=await self.bot.get_embed_color(ctx),
            title=errorType,
            description=f"```py\n{error}\n```"
        )
        embed.set_footer(text=f"Use `{ctx.prefix}help {ctx.command.qualified_name}` to see an example")
        await ctx.send(embed=embed)