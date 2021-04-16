"""
MIT License

Copyright (c) 2020-2021 phenom4n4n

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

import asyncio
import io
import json
from typing import Optional, Union

import discord
from redbot.core import Config, commands
from redbot.core.utils import menus
from redbot.core.utils.chat_formatting import box, humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, close_menu, menu, start_adding_reactions

from .converters import (
    StringToEmbed,
    StoredEmbedConverter,
    GlobalStoredEmbedConverter,
    ListStringToEmbed,
    MyMessageConverter,
    MessageableChannel,
)


YAML_CONVERTER = StringToEmbed(conversion_type="yaml")


def webhook_check(ctx: commands.Context) -> Union[bool, commands.Cog]:
    cog = ctx.bot.get_cog("Webhook")
    if (
        ctx.channel.permissions_for(ctx.me).manage_webhooks
        and cog
        and cog.__author__ == "PhenoM4n4n"
    ):
        return cog
    return False


class HelpFormattedCommand(commands.Command):
    def __init__(self, *args, **kwargs):
        add_example_info = kwargs.pop("add_example_info", False)
        super().__init__(*args, **kwargs)
        self._add_example_info = add_example_info

    def format_help_for_context(self, ctx: commands.Context):
        pre_processed = super().format_help_for_context(ctx)
        if self._add_example_info is not True:
            return pre_processed

        n = "\n" if "\n\n" not in pre_processed else ""
        output = [
            f"{pre_processed}{n}",
            "This must be in the format expected by [this Discord documentation](https://discord.com/developers/docs/resources/channel#embed-object).",
            "Here's [a json example](https://gist.github.com/TwinDragon/9cf12da39f6b2888c8d71865eb7eb6a8).",
        ]
        return "\n".join(output)


class HelpFormattedGroup(commands.Group):
    def __init__(self, *args, **kwargs):
        add_example_info = kwargs.pop("add_example_info", False)
        super().__init__(*args, **kwargs)
        self._add_example_info = add_example_info

    def format_help_for_context(self, ctx: commands.Context):
        pre_processed = super().format_help_for_context(ctx)
        if self._add_example_info is not True:
            return pre_processed

        n = "\n" if "\n\n" not in pre_processed else ""
        output = [
            f"{pre_processed}{n}",
            "This must be in the format expected by [this Discord documentation](https://discord.com/developers/docs/resources/channel#embed-object).",
            "Here's [a json example](https://gist.github.com/TwinDragon/9cf12da39f6b2888c8d71865eb7eb6a8).",
        ]
        return "\n".join(output)


class EmbedUtils(commands.Cog):
    """
    Create, post, and store embeds.
    """

    __version__ = "1.2.0"

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
    @commands.mod_or_permissions(embed_links=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.group(cls=HelpFormattedGroup, invoke_without_command=True)
    async def embed(
        self,
        ctx,
        channel: Optional[MessageableChannel],
        color: Optional[discord.Color],
        title: str,
        *,
        description: str,
    ):
        """Post a simple embed.

        Put the title in quotes if it is multiple words."""
        channel = channel or ctx.channel
        color = color or await ctx.embed_color()
        e = discord.Embed(color=color, title=title, description=description)
        await channel.send(embed=e)

    @embed.command(
        cls=HelpFormattedCommand, name="fromjson", aliases=["fromdata"], add_example_info=True
    )
    async def embed_fromjson(self, ctx, *, data: StringToEmbed):
        """
        Post an embed from valid JSON.
        """
        await ctx.tick()

    @embed.command(name="fromyaml")
    async def embed_fromyaml(self, ctx, *, data: YAML_CONVERTER):
        """
        Post an embed from valid YAML.
        """
        await ctx.tick()

    @embed.command(
        cls=HelpFormattedCommand,
        name="fromfile",
        aliases=["fromjsonfile", "fromdatafile"],
        add_example_info=True,
    )
    async def embed_fromfile(self, ctx: commands.Context):
        """
        Post an embed from a valid JSON file.
        """
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
    async def embed_frommsg(self, ctx, message: discord.Message, index: int = 0):
        """Post an embed from a message.

        If the message has multiple embeds, you can pass a number to `index` to specify which embed."""
        embed = await self.frommsg(ctx, message, index)
        if embed is None:
            return
        await ctx.send(embed=embed)

    @commands.bot_has_permissions(attach_files=True)
    @embed.command(name="download")
    async def embed_download(self, ctx, message: discord.Message, index: int = 0):
        """Download a JSON file for a message's embed.

        If the message has multiple embeds, you can pass a number to `index` to specify which embed."""
        embed = await self.frommsg(ctx, message, index)
        if embed is None:
            return
        data = embed.to_dict()
        data = json.dumps(data, indent=4)
        fp = io.BytesIO(bytes(data, "utf-8"))
        await ctx.send(file=discord.File(fp, "embed.json"))

    @embed.group(
        cls=HelpFormattedGroup,
        name="post",
        aliases=["view", "drop", "show"],
        invoke_without_command=True,
    )
    async def embed_post(
        self, ctx, name: StoredEmbedConverter, channel: MessageableChannel = None
    ):
        """Post an embed that is stored."""
        channel = channel or ctx.channel
        await channel.send(embed=discord.Embed.from_dict(name["embed"]))
        async with self.config.guild(ctx.guild).embeds() as a:
            a[name["name"]]["uses"] += 1

    @embed_post.command(name="global")
    async def embed_post_global(
        self, ctx, name: GlobalStoredEmbedConverter, channel: MessageableChannel = None
    ):
        """Post an embed that is stored globally."""
        channel = channel or ctx.channel
        await channel.send(embed=discord.Embed.from_dict(name["embed"]))
        async with self.config.embeds() as a:
            a[name["name"]]["uses"] += 1

    @embed.command(name="info")
    async def embed_info(self, ctx, name: StoredEmbedConverter):
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
    @embed.group(cls=HelpFormattedGroup, name="edit", invoke_without_command=True)
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
        Edit a message sent by [botname]'s embeds.
        """
        color = color or await ctx.embed_color()
        e = discord.Embed(color=color, title=title, description=description)
        await message.edit(embed=e)
        await ctx.tick()

    @embed_edit.command(
        cls=HelpFormattedCommand, name="fromjson", aliases=["fromdata"], add_example_info=True
    )
    async def embed_edit_fromjson(
        self, ctx: commands.Context, message: MyMessageConverter, *, data: StringToEmbed
    ):
        """
        Edit a message's embed using valid JSON.
        """
        await message.edit(embed=data)
        await ctx.tick()

    @embed_edit.command(name="fromyaml")
    async def embed_edit_fromyaml(
        self,
        ctx: commands.Context,
        message: MyMessageConverter,
        *,
        data: YAML_CONVERTER,
    ):
        """
        Edit a message's embed using valid YAML.
        """
        await message.edit(embed=data)
        await ctx.tick()

    @embed_edit.command(
        cls=HelpFormattedCommand,
        name="fromfile",
        aliases=["fromjsonfile", "fromdatafile"],
        add_example_info=True,
    )
    async def embed_edit_fromfile(self, ctx: commands.Context, message: MyMessageConverter):
        """
        Edit a message's embed using a valid JSON file.
        """
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
        if embed is None:
            return
        await target.edit(embed=embed)
        await ctx.tick()

    @commands.mod_or_permissions(manage_guild=True)
    @embed.group(name="store")
    async def embed_store(self, ctx):
        """Store embeds for server use."""

    @embed_store.command(name="remove", aliases=["delete", "rm", "del"])
    async def embed_store_remove(self, ctx, name):
        """Remove a stored embed on this server."""
        try:
            async with self.config.guild(ctx.guild).embeds() as a:
                del a[name]
            await ctx.send("Embed deleted.")
        except KeyError:
            await ctx.send("This is not a stored embed.")

    @embed_store.command(name="download")
    async def embed_store_download(self, ctx: commands.Context, embed: StoredEmbedConverter):
        """Download a JSON file for a stored embed."""
        data = json.dumps(embed["embed"], indent=4)
        fp = io.BytesIO(bytes(data, "utf-8"))
        await ctx.send(file=discord.File(fp, "embed.json"))

    @embed_store.command(name="list")
    async def embed_store_list(self, ctx):
        """View stored embeds."""
        _embeds = await self.config.guild(ctx.guild).embeds()
        if not _embeds:
            return await ctx.send("There are no stored embeds on this server.")
        description = [f"`{embed}`" for embed in _embeds]

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
            controls = {"❌": close_menu}
            await menu(ctx, [e], controls)

    @embed_store.command(name="simple")
    async def embed_store_simple(
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

    @embed_store.command(
        cls=HelpFormattedCommand, name="fromjson", aliases=["fromdata"], add_example_info=True
    )
    async def embed_store_fromjson(self, ctx, name: str, *, data: StringToEmbed):
        """
        Store an embed from valid JSON on this server.
        """
        await self.store_embed(ctx, name, data)
        await ctx.tick()

    @embed_store.command(name="fromyaml")
    async def embed_store_fromyaml(
        self, ctx, name: str, *, data: YAML_CONVERTER
    ):
        """
        Store an embed from valid YAML on this server.
        """
        await self.store_embed(ctx, name, data)
        await ctx.tick()

    @embed_store.command(
        cls=HelpFormattedCommand,
        name="fromfile",
        aliases=["fromjsonfile", "fromdatafile"],
        add_example_info=True,
    )
    async def embed_store_fromfile(self, ctx, name: str):
        """
        Store an embed from a valid JSON file on this server.
        """
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

    @embed_store.command(name="frommsg", aliases=["frommessage"])
    async def embed_store_frommsg(self, ctx, name: str, message: discord.Message, index: int = 0):
        """Store an embed from a message on this server.

        If the message has multiple embeds, you can pass a number to `index` to specify which embed."""
        embed = await self.frommsg(ctx, message, index)
        if embed is None:
            return
        await ctx.send(embed=embed)
        await self.store_embed(ctx, name, embed)

    @commands.is_owner()
    @embed.group(name="global")
    async def global_store(self, ctx):
        """Store embeds for global use."""
        if ctx.subcommand_passed:
            return

        embeds = await self.config.embeds()
        if embeds is None:
            return
        description = [f"`{embed}`" for embed in embeds]

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
        description = [f"`{embed}`" for embed in embeds]

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

    @global_store.command(
        cls=HelpFormattedCommand, name="fromjson", aliases=["fromdata"], add_example_info=True
    )
    async def global_store_fromjson(self, ctx, name: str, locked: bool, *, data: StringToEmbed):
        """Store an embed from valid JSON globally.

        The `locked` argument specifies whether the embed should be locked to owners only."""
        await self.global_store_embed(ctx, name, data, locked)
        await ctx.tick()

    @global_store.command(
        cls=HelpFormattedCommand,
        name="fromfile",
        aliases=["fromjsonfile", "fromdatafile"],
        add_example_info=True,
    )
    async def global_store_fromfile(self, ctx, name: str, locked: bool):
        """Store an embed from a valid JSON file globally.

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
        if embed is None:
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

    @webhook.command(
        cls=HelpFormattedCommand, name="fromjson", aliases=["fromdata"], add_example_info=True
    )
    async def webhook_fromjson(self, ctx: commands.Context, *, embeds: ListStringToEmbed):
        """
        Send embeds through webhooks using JSON.
        """
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

    @webhook.command(name="fromyaml")
    async def webhook_fromyaml(
        self, ctx: commands.Context, *, embeds: ListStringToEmbed(conversion_type="yaml") # noqa: F821
    ):
        """
        Send embeds through webhooks using YAML.
        """
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

    @webhook.command(name="frommsg", aliases=["frommessage"])
    async def webhook_frommsg(
        self, ctx: commands.Context, message: discord.Message, index: int = 0
    ):
        """
        Send embeds through webhooks.
        """
        embed = await self.frommsg(ctx, message, index)
        if embed is None:
            return
        cog = self.bot.get_cog("Webhook")
        try:
            await cog.send_to_channel(
                ctx.channel,
                ctx.me,
                ctx.author,
                ctx=ctx,
                embed=embed,
            )
        except discord.HTTPException as error:
            await self.embed_convert_error(ctx, "Embed Send Error", error)

    @webhook.command(
        cls=HelpFormattedCommand,
        name="fromfile",
        aliases=["fromjsonfile", "fromdatafile"],
        add_example_info=True,
    )
    async def webhook_fromfile(self, ctx: commands.Context):
        """
        Send embeds through webhooks, using files.
        """
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
            if data["locked"] == True and not await self.bot.is_owner(ctx.author):
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
            await ctx.send("This is not a valid embed/index.")
            return
        except IndexError:
            await ctx.send("This is not a valid embed/index.")
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
        await menus.menu(ctx, [embed], {"❌": menus.close_menu})
