import asyncio
import io
import json
from typing import Optional, Union

import discord
from redbot.core import Config, checks, commands
from redbot.core.utils import menus
from redbot.core.utils.chat_formatting import box, humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, close_menu, menu, start_adding_reactions

from .converters import (
    StringToEmbed,
    StoredEmbedConverter,
    GlobalStoredEmbedConverter,
    ListStringToEmbed,
    MyMessageConverter,
)


def webhook_check(ctx: commands.Context) -> Union[bool, commands.Cog]:
    cog = ctx.bot.get_cog("Webhook")
    if (
        ctx.channel.permissions_for(ctx.me).manage_webhooks
        and cog
        and cog.__author__ == "PhenoM4n4n"
    ):
        return cog
    return False


class EmbedUtils(commands.Cog):
    """
    Create, post, and store embeds.
    """

    __version__ = "1.1.4"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=43248937299564234735284,
            force_registration=True,
        )
        default_global = {"embeds": {}}
        default_guild = {"embeds": {}}
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(self, *, requester: str, user_id: int):
        guilds_data = await self.config.all_guilds()
        for guild_id, data in guilds_data.items():
            guild = self.bot.get_guild(guild_id)
            if guild and data["embeds"]:
                for name, embed in data["embeds"].items():
                    if str(user_id) in embed["author"]:
                        async with self.config.guild(guild).embeds() as e:
                            del e[name]
        global_data = await self.config.all()
        if global_data["embeds"]:
            for name, embed in global_data["embeds"].items():
                if str(user_id) in embed["author"]:
                    async with self.config.embeds() as e:
                        del e[name]

    @commands.guild_only()
    @checks.mod_or_permissions(embed_links=True)
    @checks.bot_has_permissions(embed_links=True)
    @commands.group(invoke_without_command=True)
    async def embed(
        self,
        ctx,
        channel: Optional[discord.TextChannel],
        color: Optional[discord.Color],
        title: str,
        *,
        description: str,
    ):
        """Post a simple embed.

        Put the title in quotes if it is multiple words."""
        channel = channel or ctx.channel
        my_perms = channel.permissions_for(ctx.me)
        auth_perms = channel.permissions_for(ctx.author)
        if not (
            (my_perms.send_messages and my_perms.embed_links)
            and (auth_perms.send_messages and auth_perms.embed_links)
        ):
            raise commands.BadArgument
        color = color or await ctx.embed_color()
        e = discord.Embed(color=color, title=title, description=description)
        await channel.send(embed=e)

    @embed.command(aliases=["fromjson"])
    async def fromdata(self, ctx, *, data: StringToEmbed):
        """Post an embed from valid JSON.

        This must be in the format expected by [this Discord documenation](https://discord.com/developers/docs/resources/channel#embed-object "Click me!").
        Here's [a json example](https://gist.github.com/TwinDragon/9cf12da39f6b2888c8d71865eb7eb6a8 "Click me!")."""
        await ctx.tick()

    @embed.command(aliases=["fromjsonfile", "fromdatafile"])
    async def fromfile(self, ctx):
        """Post an embed from a valid JSON file.

        This doesn't actually need to be a `.json` file, but it should follow the format expected by [this Discord documenation](https://discord.com/developers/docs/resources/channel#embed-object "Click me!").
        Here's [a json example](https://gist.github.com/TwinDragon/9cf12da39f6b2888c8d71865eb7eb6a8 "Click me!")."""
        if not ctx.message.attachments:
            return await ctx.send("You need to provide a file for this..")
        attachment = ctx.message.attachments[0]
        content = await attachment.read()
        try:
            data = content.decode("utf-8")
        except UnicodeDecodeError:
            return await ctx.send("That's not an actual embed file wyd")
        await StringToEmbed().convert(ctx, data)
        await ctx.tick()

    @embed.command(name="frommsg", aliases=["frommessage"])
    async def com_frommsg(self, ctx, message: discord.Message, index: int = 0):
        """Post an embed from a message.

        If the message has multiple embeds, you can pass a number to `index` to specify which embed."""
        embed = await self.frommsg(ctx, message, index)
        if not embed:
            return
        await ctx.send(embed=embed)

    @checks.bot_has_permissions(attach_files=True)
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

    @embed.group(name="show", aliases=["view", "drop"], invoke_without_command=True)
    async def com_drop(self, ctx, name: StoredEmbedConverter):
        """View an embed that is stored."""
        await ctx.send(embed=discord.Embed.from_dict(name["embed"]))
        async with self.config.guild(ctx.guild).embeds() as a:
            a[name["name"]]["uses"] += 1

    @com_drop.command(name="global")
    async def global_drop(self, ctx, name: GlobalStoredEmbedConverter):
        """View an embed that is stored globally."""
        await ctx.send(embed=discord.Embed.from_dict(name["embed"]))
        async with self.config.embeds() as a:
            a[name["name"]]["uses"] += 1

    @embed.command(name="info")
    async def com_info(self, ctx, name: StoredEmbedConverter):
        """Get info about an embed that is stored on this server."""
        e = discord.Embed(
            title=f"`{name['name']}` Info",
            description=(
                f"Author: <@!{name['author']}>\nUses: {name['uses']}\n"
                f"Length: {len(name['embed'])}"
            ),
        )
        e.set_author(name=ctx.bot.user.name, icon_url=ctx.bot.user.avatar_url)
        await ctx.send(embed=e)

    @embed.command(aliases=["delete", "rm", "del"])
    async def remove(self, ctx, name):
        """Remove a stored embed on this server."""
        try:
            async with self.config.guild(ctx.guild).embeds() as a:
                del a[name]
            await ctx.send("Embed deleted.")
        except KeyError:
            await ctx.send("This is not a stored embed.")

    @embed.command(name="clear", hidden=True)
    async def clear(self, ctx):
        """Remove ALL embed data from the bot."""
        await ctx.send(
            "This will remove ALL embed data, including global data, from the bot. Are you sure you want to continue? (yes/no)"
        )
        try:
            message = await self.bot.wait_for(
                "message",
                check=lambda x: x.channel == ctx.channel
                and x.author == ctx.author
                and (x.content.lower().startswith("yes") or x.content.lower().startswith("no")),
                timeout=30,
            )
            if message.content.lower().startswith("no"):
                return await ctx.send("Ok, not removing this data..")
            await self.config.clear_all()
            await ctx.tick()
        except asyncio.TimeoutError:
            await ctx.send("Ok, not removing this data..")

    @commands.mod_or_permissions(manage_messages=True)
    @embed.group(name="edit", invoke_without_command=True)
    async def embed_edit(
        self,
        ctx: commands.Context,
        message: MyMessageConverter,
        color: Optional[discord.Color],
        title: str,
        *,
        description: str,
    ):
        """
        Edit a message sent by me's embeds.
        """
        color = color or await ctx.embed_color()
        e = discord.Embed(color=color, title=title, description=description)
        await message.edit(embed=e)
        await ctx.tick()

    @embed_edit.command(name="fromdata", aliases=["fromjson"])
    async def embed_edit_fromdata(
        self, ctx: commands.Context, message: MyMessageConverter, *, data: StringToEmbed
    ):
        """Edit a message's embed using valid JSON.

        This must be in the format expected by [this Discord documenation](https://discord.com/developers/docs/resources/channel#embed-object "Click me!").
        Here's [a json example](https://gist.github.com/TwinDragon/9cf12da39f6b2888c8d71865eb7eb6a8 "Click me!")."""
        await message.edit(embed=data)
        await ctx.tick()

    @embed_edit.command(name="fromfile", aliases=["fromjsonfile", "fromdatafile"])
    async def embed_edit_fromfile(self, ctx: commands.Context, message: MyMessageConverter):
        """Edit a message's embed using a valid JSON file.

        This doesn't actually need to be a `.json` file, but it should follow the format expected by [this Discord documenation](https://discord.com/developers/docs/resources/channel#embed-object "Click me!").
        Here's [a json example](https://gist.github.com/TwinDragon/9cf12da39f6b2888c8d71865eb7eb6a8 "Click me!")."""
        if not ctx.message.attachments:
            return await ctx.send("You need to provide a file for this..")
        attachment = ctx.message.attachments[0]
        content = await attachment.read()
        try:
            data = content.decode("utf-8")
        except UnicodeDecodeError:
            return await ctx.send("That's not an actual embed file wyd")
        e = await StringToEmbed().convert(ctx, data)
        await message.edit(embed=e)
        await ctx.tick()

    @embed_edit.command(name="frommsg", aliases=["frommessage"])
    async def embed_edit_frommsg(
        self,
        ctx: commands.Context,
        source: discord.Message,
        target: MyMessageConverter,
        index: int = 0,
    ):
        """Edit a message's embed using another message's embed.

        If the message has multiple embeds, you can pass a number to `index` to specify which embed."""
        embed = await self.frommsg(ctx, source, index)
        if not embed:
            return
        await target.edit(embed=embed)
        await ctx.tick()

    @checks.mod_or_permissions(manage_guild=True)
    @embed.group()
    async def store(self, ctx):
        """Store embeds for server use."""
        if not ctx.subcommand_passed:
            embeds = await self.config.guild(ctx.guild).embeds()
            description = []

            if not embeds:
                return
            for embed in embeds:
                description.append(f"`{embed}`")
            description = "\n".join(description)

            color = await self.bot.get_embed_colour(ctx)
            e = discord.Embed(color=color, title=f"Stored Embeds", description=description)
            e.set_author(name=ctx.guild, icon_url=ctx.guild.icon_url)
            await ctx.send(embed=e)

    @embed.command(name="list")
    async def store_list(self, ctx):
        """View stored embeds."""
        _embeds = await self.config.guild(ctx.guild).embeds()
        if not _embeds:
            return await ctx.send("There are no stored embeds on this server.")
        description = []

        for embed in _embeds:
            description.append(f"`{embed}`")
        description = "\n".join(description)

        color = await self.bot.get_embed_colour(ctx)
        e = discord.Embed(color=color, title=f"Stored Embeds")
        e.set_author(name=ctx.guild, icon_url=ctx.guild.icon_url)

        if len(description) > 2048:
            embeds = []
            pages = list(pagify(description, page_length=1024))
            for index, page in enumerate(pages, start=1):
                embed = e.copy()
                embed.description = page
                embed.set_footer(text=f"{index}/{len(pages)}")
                embeds.append(embed)
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            e.description = description
            emoji = self.bot.get_emoji(736038541364297738) or "❌"
            controls = {emoji: close_menu}
            await menu(ctx, [e], controls)

    @store.command(name="simple")
    async def store_simple(
        self,
        ctx,
        name: str,
        color: Optional[discord.Color],
        title: str,
        *,
        description: str,
    ):
        """Store a simple embed on this server.

        Put the title in quotes if it is multiple words."""
        if not color:
            color = await self.bot.get_embed_color(ctx)
        e = discord.Embed(color=color, title=title, description=description)
        await ctx.send(embed=e)
        await self.store_embed(ctx, name, e)
        await ctx.tick()

    @store.command(name="fromdata", aliases=["fromjson"])
    async def store_fromdata(self, ctx, name: str, *, data: StringToEmbed):
        """Store an embed from valid JSON on this server.

        This must be in the format expected by [this Discord documenation](https://discord.com/developers/docs/resources/channel#embed-object "Click me!").
        Here's [a json example](https://gist.github.com/TwinDragon/9cf12da39f6b2888c8d71865eb7eb6a8 "Click me!")."""
        await self.store_embed(ctx, name, data)
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
            return await ctx.send("That's not an actual embed file wyd")
        e = await StringToEmbed().convert(ctx, data)
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

    @checks.is_owner()
    @embed.group(name="global")
    async def global_store(self, ctx):
        """Store embeds for global use."""
        if not ctx.subcommand_passed:
            embeds = await self.config.embeds()
            description = []

            if not embeds:
                return
            for embed in embeds:
                description.append(f"`{embed}`")
            description = "\n".join(description)

            color = await self.bot.get_embed_colour(ctx)
            e = discord.Embed(color=color, title=f"Stored Embeds", description=description)
            e.set_author(name=ctx.bot.user.name, icon_url=ctx.bot.user.avatar_url)
            await ctx.send(embed=e)

    @global_store.command(name="remove", aliases=["delete", "rm", "del"])
    async def global_remove(self, ctx, name):
        """Remove a global embed."""
        try:
            async with self.config.embeds() as a:
                del a[name]
            await ctx.send("Embed deleted.")
        except KeyError:
            await ctx.send("This is not a stored embed.")

    @global_store.command(name="list")
    async def global_list(self, ctx):
        """View global embeds."""
        embeds = await self.config.embeds()
        description = []

        for embed in embeds:
            description.append(f"`{embed}`")
        description = "\n".join(description)

        color = await self.bot.get_embed_colour(ctx)
        e = discord.Embed(color=color, title=f"Stored Embeds", description=description)
        e.set_author(name=ctx.bot.user.name, icon_url=ctx.bot.user.avatar_url)
        await ctx.send(embed=e)

    @global_store.command(name="simple")
    async def global_store_simple(
        self,
        ctx,
        name: str,
        locked: bool,
        color: Optional[discord.Color],
        title: str,
        *,
        description: str,
    ):
        """Store a simple embed globally.

        Put the title in quotes if it is multiple words.
        The `locked` argument specifies whether the embed should be locked to owners only."""
        if not color:
            color = await self.bot.get_embed_color(ctx)
        e = discord.Embed(color=color, title=title, description=description)
        await ctx.send(embed=e)
        await self.global_store_embed(ctx, name, e, locked)
        await ctx.tick()

    @global_store.command(name="fromdata", aliases=["fromjson"])
    async def global_store_fromdata(self, ctx, name: str, locked: bool, *, data: StringToEmbed):
        """Store an embed from valid JSON globally.

        This must be in the format expected by [this Discord documenation](https://discord.com/developers/docs/resources/channel#embed-object "Click me!").
        Here's [a json example](https://gist.github.com/TwinDragon/9cf12da39f6b2888c8d71865eb7eb6a8 "Click me!").
        The `locked` argument specifies whether the embed should be locked to owners only."""
        await self.global_store_embed(ctx, name, data, locked)
        await ctx.tick()

    @global_store.command(name="fromfile", aliases=["fromjsonfile", "fromdatafile"])
    async def global_store_fromfile(self, ctx, name: str, locked: bool):
        """Store an embed from a valid JSON file globally.

        This doesn't actually need to be a `.json` file, but it should follow the format expected by [this Discord documenation](https://discord.com/developers/docs/resources/channel#embed-object "Click me!").
        Here's [a json example](https://gist.github.com/TwinDragon/9cf12da39f6b2888c8d71865eb7eb6a8 "Click me!").
        The `locked` argument specifies whether the embed should be locked to owners only."""
        if not ctx.message.attachments:
            return await ctx.send("You need to provide a file for this..")
        attachment = ctx.message.attachments[0]
        content = await attachment.read()
        try:
            data = content.decode("utf-8")
        except UnicodeDecodeError:
            return await ctx.send("That's not an actual embed file wyd")
        e = await StringToEmbed().convert(ctx, data)
        if e:
            await self.global_store_embed(ctx, name, e, locked)
        await ctx.tick()

    @global_store.command(name="frommsg", aliases=["frommessage"])
    async def global_store_frommsg(
        self, ctx, name: str, message: discord.Message, locked: bool, index: int = 0
    ):
        """Store an embed from a message globally.

        If the message has multiple embeds, you can pass a number to `index` to specify which embed.
        The `locked` argument specifies whether the embed should be locked to owners only."""
        embed = await self.frommsg(ctx, message, index)
        if not embed:
            return
        await ctx.send(embed=embed)
        await self.global_store_embed(ctx, name, embed, locked)

    @global_store.command(name="info")
    async def global_info(self, ctx, name: GlobalStoredEmbedConverter):
        """Get info about an embed that is stored globally."""
        e = discord.Embed(
            title=f"`{name['name']}` Info",
            description=(
                f"Author: <@!{name['author']}>\nUses: {name['uses']}\n"
                f"Length: {len(name['embed'])}\nLocked: {name['locked']}"
            ),
        )
        e.set_author(name=ctx.bot.user.name, icon_url=ctx.bot.user.avatar_url)
        await ctx.send(embed=e)

    @global_store.command(name="lock")
    async def global_lock(self, ctx, name: str, true_or_false: bool = None):
        """Lock/unlock a global embed."""
        data = await self.config.embeds()
        try:
            embed = data[name]
        except KeyError:
            await ctx.send("This is not a stored embed.")
            return
        target_state = true_or_false if true_or_false is not None else not embed["locked"]
        async with self.config.embeds() as a:
            a[name]["locked"] = target_state
        if target_state:
            await ctx.send(f"`{name}` is now locked to owners only.")
        else:
            await ctx.send(f"`{name}` is now accessible to all users.")

    @commands.check(webhook_check)
    @commands.admin_or_permissions(manage_webhooks=True)
    @commands.bot_has_permissions(manage_webhooks=True)
    @embed.group(invoke_without_command=True)
    async def webhook(self, ctx: commands.Context, *embeds: StoredEmbedConverter):
        """Send embeds through webhooks.

        Running this command with stored embed names will send up to 10 embeds through a webhook."""
        if not embeds:
            raise commands.BadArgument()
        cog = self.bot.get_cog("Webhook")
        await cog.send_to_channel(
            ctx.channel,
            ctx.me,
            ctx.author,
            ctx=ctx,
            embeds=[discord.Embed.from_dict(e["embed"]) for e in embeds[:10]],
        )

    @webhook.command(name="global")
    async def webhook_global(self, ctx: commands.Context, *embeds: GlobalStoredEmbedConverter):
        """Send global embeds through webhooks.

        Running this command with global stored embed names will send up to 10 embeds through a webhook."""
        if not embeds:
            raise commands.BadArgument()
        cog = self.bot.get_cog("Webhook")
        await cog.send_to_channel(
            ctx.channel,
            ctx.me,
            ctx.author,
            ctx=ctx,
            embeds=[discord.Embed.from_dict(e["embed"]) for e in embeds[:10]],
        )

    @webhook.command(name="fromdata", aliases=["fromjson"])
    async def webhook_fromdata(self, ctx: commands.Context, *, embeds: ListStringToEmbed):
        """Send embeds through webhooks.

        This must be in the format expected by [this Discord documenation](https://discord.com/developers/docs/resources/channel#embed-object "Click me!").
        Here's [a json example](https://gist.github.com/TwinDragon/9cf12da39f6b2888c8d71865eb7eb6a8 "Click me!")."""
        cog = self.bot.get_cog("Webhook")
        try:
            await cog.send_to_channel(
                ctx.channel,
                ctx.me,
                ctx.author,
                ctx=ctx,
                embeds=embeds[:10],
            )
        except discord.HTTPException as error:
            await self.embed_convert_error(ctx, "Embed Send Error", error)

    @webhook.command(name="fromfile", aliases=["fromjsonfile", "fromdatafile"])
    async def webhook_fromfile(self, ctx: commands.Context):
        """Send embeds through webhooks, using files.

        This must be in the format expected by [this Discord documenation](https://discord.com/developers/docs/resources/channel#embed-object "Click me!").
        Here's [a json example](https://gist.github.com/TwinDragon/9cf12da39f6b2888c8d71865eb7eb6a8 "Click me!")."""
        if not ctx.message.attachments:
            return await ctx.send("You need to provide a file for this..")
        attachment = ctx.message.attachments[0]
        content = await attachment.read()
        try:
            data = content.decode("utf-8")
        except UnicodeDecodeError:
            return await ctx.send("That's not an actual embed file wyd")
        embeds = await ListStringToEmbed().convert(ctx, data)
        cog = self.bot.get_cog("Webhook")
        try:
            await cog.send_to_channel(
                ctx.channel,
                ctx.me,
                ctx.author,
                ctx=ctx,
                embeds=embeds[:10],
            )
        except discord.HTTPException as error:
            await self.embed_convert_error(ctx, "Embed Send Error", error)

    async def store_embed(self, ctx: commands.Context, name: str, embed: discord.Embed):
        embed = embed.to_dict()
        async with self.config.guild(ctx.guild).embeds() as a:
            a[name] = {"author": ctx.author.id, "uses": 0, "embed": embed}
        await ctx.send(f"Embed stored under the name `{name}`.")

    async def get_stored_embed(self, ctx: commands.Context, name: str):
        data = await self.config.guild(ctx.guild).embeds()
        try:
            data = data[name]
            embed = data["embed"]
        except KeyError:
            await ctx.send("This is not a stored embed.")
            return
        embed = discord.Embed.from_dict(embed)
        return embed, data["author"], data["uses"]

    async def global_store_embed(
        self, ctx: commands.Context, name: str, embed: discord.Embed, locked: bool
    ):
        embed = embed.to_dict()
        async with self.config.embeds() as a:
            a[name] = {"author": ctx.author.id, "uses": 0, "locked": locked, "embed": embed}
        await ctx.send(f"Global embed stored under the name `{name}`.")

    async def get_global_stored_embed(self, ctx: commands.Context, name: str):
        data = await self.config.embeds()
        try:
            data = data[name]
            embed = data["embed"]
            if data["locked"] == True:
                if not await self.bot.is_owner(ctx.author):
                    await ctx.send("This is not a stored embed.")
                    return
        except KeyError:
            await ctx.send("This is not a stored embed.")
            return
        embed = discord.Embed.from_dict(embed)
        return embed, data["author"], data["uses"], data["locked"]

    async def frommsg(self, ctx: commands.Context, message: discord.Message, index: int = 0):
        try:
            embed = message.embeds[index]
            if embed.type == "rich":
                return embed
            else:
                await ctx.send("This is not a valid embed/index.")
                return
        except IndexError:
            await ctx.send("This is not a valid embed/index.")
            return

    async def str_embed_converter(self, ctx, data):
        data = data.strip("`")
        try:
            data = json.loads(data)
        except json.decoder.JSONDecodeError as error:
            await self.embed_convert_error(ctx, "JSON Parse Error", error)
            return
        if data.get("embed"):
            data = data["embed"]
        if data.get("timestamp"):
            data["timestamp"] = data["timestamp"].strip("Z")
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

    async def embed_convert_error(self, ctx: commands.Context, error_type: str, error: Exception):
        embed = discord.Embed(
            color=await ctx.embed_color(),
            title=error_type,
            description=f"```py\n{error}\n```",
        )
        embed.set_footer(
            text=f"Use `{ctx.prefix}help {ctx.command.qualified_name}` to see an example"
        )
        emoji = ctx.bot.get_emoji(736038541364297738) or "❌"
        await menus.menu(ctx, [embed], {emoji: menus.close_menu})
