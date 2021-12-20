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

import aiohttp
import discord
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import humanize_list, inline, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, close_menu, menu

from .commands import help_formatted_group
from .converters import (
    GlobalStoredEmbedConverter,
    ListStringToEmbed,
    MessageableChannel,
    MyMessageConverter,
    PastebinConverter,
    PastebinConverterWebhook,
    StoredEmbedConverter,
    StringToEmbed,
)
from .errors import EmbedConversionError, EmbedFileError, EmbedNotFound, EmbedUtilsException

JSON_CONVERTER = StringToEmbed()
JSON_CONTENT_CONVERTER = StringToEmbed(content=True)
YAML_CONVERTER = StringToEmbed(conversion_type="yaml")
YAML_CONTENT_CONVERTER = StringToEmbed(conversion_type="yaml", content=True)
PASTEBIN_CONVERTER = PastebinConverter(conversion_type="yaml")
PASTEBIN_CONTENT_CONVERTER = PastebinConverter(conversion_type="yaml", content=True)


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

    __version__ = "1.5.0"

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
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        asyncio.create_task(self.session.close())

    async def red_delete_data_for_user(self, *, requester: str, user_id: int):
        guilds_data = await self.config.all_guilds()
        for guild_id, data in guilds_data.items():
            guild = self.bot.get_guild(guild_id)
            if guild and data["embeds"]:
                for name, embed in data["embeds"].items():
                    if user_id == embed["author"]:
                        async with self.config.guild(guild).embeds() as e:
                            del e[name]
        global_data = await self.config.all()
        if global_data["embeds"]:
            for name, embed in global_data["embeds"].items():
                if user_id == embed["author"]:
                    async with self.config.embeds() as e:
                        del e[name]

    async def get_embed_from_message(
        self, ctx: commands.Context, message: discord.Message, index: int = 0
    ):
        embeds = message.embeds
        if not embeds:
            raise EmbedNotFound("That message has no embeds.")
        index = max(min(index, len(embeds)), 0)
        embed = message.embeds[index]
        if embed.type == "rich":
            return embed
        raise EmbedNotFound("That is not a rich embed.")

    async def get_file_from_message(
        self, ctx: commands.Context, *, file_types=("json", "txt", "yaml")
    ) -> str:
        if not ctx.message.attachments:
            raise EmbedFileError(
                f"Run `{ctx.clean_prefix}{ctx.command.qualified_name}` again, but this time "
                "attach an embed file."
            )
        attachment = ctx.message.attachments[0]
        if not any(attachment.filename.endswith("." + ft) for ft in file_types):
            file_names = humanize_list([inline(ft) for ft in file_types])
            raise EmbedFileError(
                f"Invalid file type. The file name must end with one of {file_names}."
            )

        content = await attachment.read()
        try:
            data = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EmbedFileError("Failed to read embed file contents.") from exc
        return data

    @commands.guild_only()
    @commands.mod_or_permissions(embed_links=True)
    @commands.bot_has_permissions(embed_links=True)
    @help_formatted_group(invoke_without_command=True)
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

    @embed.command(name="json", aliases=["fromjson", "fromdata"], add_example_info=True)
    async def embed_json(
        self,
        ctx: commands.Context,
        channel: Optional[MessageableChannel] = None,
        *,
        data: JSON_CONTENT_CONVERTER,
    ):
        """
        Post an embed from valid JSON.
        """
        if channel and channel != ctx.channel:
            await channel.send(embed=data)
        await ctx.tick()

    @embed.command(name="yaml", aliases=["fromyaml"], add_example_info=True, info_type="yaml")
    async def embed_yaml(
        self,
        ctx: commands.Context,
        channel: Optional[MessageableChannel] = None,
        *,
        data: YAML_CONTENT_CONVERTER,
    ):
        """
        Post an embed from valid YAML.
        """
        if channel and channel != ctx.channel:
            await channel.send(embed=data)
        await ctx.tick()

    @embed.command(
        name="pastebin", aliases=["frompaste"], add_example_info=True, info_type="pastebin"
    )
    async def embed_pastebin(
        self,
        ctx: commands.Context,
        channel: Optional[MessageableChannel] = None,
        *,
        data: PASTEBIN_CONTENT_CONVERTER,
    ):
        """
        Post an embed from a pastebin link containing valid JSON or YAML.
        """
        if channel and channel != ctx.channel:
            await channel.send(embed=data)
        await ctx.tick()

    @embed.command(
        name="fromfile",
        aliases=["fromjsonfile", "fromdatafile"],
        add_example_info=True,
    )
    async def embed_fromfile(self, ctx: commands.Context, channel: MessageableChannel = None):
        """
        Post an embed from a valid JSON file.
        """
        data = await self.get_file_from_message(ctx, file_types=("json", "txt"))
        embed = await JSON_CONTENT_CONVERTER.convert(ctx, data)
        if channel and channel != ctx.channel:
            await channel.send(embed=embed)
        await ctx.tick()

    @embed.command(
        name="yamlfile",
        aliases=["fromyamlfile"],
        add_example_info=True,
        info_type="yaml",
    )
    async def embed_yamlfile(self, ctx: commands.Context, channel: MessageableChannel = None):
        """
        Post an embed from a valid YAML file.
        """
        data = await self.get_file_from_message(ctx, file_types=("yaml", "txt"))
        embed = await YAML_CONTENT_CONVERTER.convert(ctx, data)
        if channel and channel != ctx.channel:
            await channel.send(embed=embed)
        await ctx.tick()

    @embed.command(
        name="message",
        aliases=["frommsg", "frommessage"],
        add_example_info=True,
        info_type="index",
    )
    async def embed_message(
        self,
        ctx,
        message: discord.Message,
        index: Optional[int] = 0,
        channel: MessageableChannel = None,
    ):
        """
        Post an embed from a message.
        """
        embed = await self.get_embed_from_message(ctx, message, index)
        channel = channel or ctx.channel
        await channel.send(embed=embed)
        await ctx.tick()

    @commands.bot_has_permissions(attach_files=True)
    @embed.command(name="download", add_example_info=True, info_type="index")
    async def embed_download(self, ctx, message: discord.Message, index: int = 0):
        """
        Download a JSON file for a message's embed.
        """
        embed = await self.get_embed_from_message(ctx, message, index)
        data = embed.to_dict()
        data = json.dumps(data, indent=4)
        fp = io.BytesIO(bytes(data, "utf-8"))
        await ctx.send(file=discord.File(fp, "embed.json"))

    @embed.group(
        name="post",
        aliases=["view", "drop", "show"],
        invoke_without_command=True,
    )
    async def embed_post(
        self, ctx, name: StoredEmbedConverter, channel: MessageableChannel = None
    ):
        """Post a stored embed."""
        channel = channel or ctx.channel
        await channel.send(embed=discord.Embed.from_dict(name["embed"]))
        async with self.config.guild(ctx.guild).embeds() as a:
            a[name["name"]]["uses"] += 1

    @embed_post.command(name="global")
    async def embed_post_global(
        self, ctx, name: GlobalStoredEmbedConverter, channel: MessageableChannel = None
    ):
        """Post a global stored embed."""
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
        Edit a message sent by [botname]'s embeds.
        """
        color = color or await ctx.embed_color()
        e = discord.Embed(color=color, title=title, description=description)
        await message.edit(embed=e)
        await ctx.tick()

    @embed_edit.command(name="json", aliases=["fromjson", "fromdata"], add_example_info=True)
    async def embed_edit_json(
        self, ctx: commands.Context, message: MyMessageConverter, *, data: JSON_CONVERTER
    ):
        """
        Edit a message's embed using valid JSON.
        """
        await message.edit(embed=data)
        await ctx.tick()

    @embed_edit.command(name="yaml", aliases=["fromyaml"])
    async def embed_edit_yaml(
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
        name="pastebin", aliases=["frompaste"], add_example_info=True, info_type="pastebin"
    )
    async def embed_edit_pastebin(
        self,
        ctx: commands.Context,
        message: MyMessageConverter,
        *,
        data: PASTEBIN_CONVERTER,
    ):
        """
        Edit a message's embed using a pastebin link which contains valid JSON or YAML.
        """
        await message.edit(embed=data)
        await ctx.tick()

    @embed_edit.command(
        name="fromfile",
        aliases=["fromjsonfile", "fromdatafile"],
        add_example_info=True,
    )
    async def embed_edit_fromfile(self, ctx: commands.Context, message: MyMessageConverter):
        """
        Edit a message's embed using a valid JSON file.
        """
        data = await self.get_file_from_message(ctx, file_types=("json", "txt"))
        e = await JSON_CONVERTER.convert(ctx, data)
        await message.edit(embed=e)
        await ctx.tick()

    @embed_edit.command(
        name="yamlfile",
        aliases=["fromyamlfile"],
        add_example_info=True,
        info_type="yaml",
    )
    async def embed_edit_yamlfile(self, ctx: commands.Context, message: MyMessageConverter):
        """
        Edit a message's embed using a valid YAML file.
        """
        data = await self.get_file_from_message(ctx, file_types=("yaml", "txt"))
        e = await YAML_CONVERTER.convert(ctx, data)
        await message.edit(embed=e)
        await ctx.tick()

    @embed_edit.command(
        name="message",
        aliases=["frommsg", "frommessage"],
        add_example_info=True,
        info_type="index",
    )
    async def embed_edit_message(
        self,
        ctx: commands.Context,
        source: discord.Message,
        target: MyMessageConverter,
        index: int = 0,
    ):
        """
        Edit a message's embed using another message's embed.
        """
        embed = await self.get_embed_from_message(ctx, source, index)
        await target.edit(embed=embed)
        await ctx.tick()

    @embed_edit.group("store", aliases=["stored"], invoke_without_command=True)
    async def embed_edit_store(
        self, ctx: commands.Context, message: MyMessageConverter, name: StoredEmbedConverter
    ):
        """
        Edit a message's embed using an embed that's stored on this server.
        """
        embed = discord.Embed.from_dict(name["embed"])
        await message.edit(embed=embed)
        await ctx.tick()
        async with self.config.guild(ctx.guild).embeds() as a:
            a[name["name"]]["uses"] += 1

    @embed_edit_store.command("global")
    async def embed_edit_store_global(
        self, ctx: commands.Context, message: MyMessageConverter, name: GlobalStoredEmbedConverter
    ):
        """
        Edit a message's embed using an embed that's stored globally.
        """
        embed = discord.Embed.from_dict(name["embed"])
        await message.edit(embed=embed)
        await ctx.tick()
        async with self.config.embeds() as a:
            a[name["name"]]["uses"] += 1

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
        e = discord.Embed(color=color, title="Stored Embeds")
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

    @embed_store.command(name="json", aliases=["fromjson", "fromdata"], add_example_info=True)
    async def embed_store_json(self, ctx, name: str, *, data: JSON_CONVERTER):
        """
        Store an embed from valid JSON on this server.
        """
        await self.store_embed(ctx, name, data)
        await ctx.tick()

    @embed_store.command(
        name="yaml", aliases=["fromyaml"], add_example_info=True, info_type="yaml"
    )
    async def embed_store_yaml(self, ctx, name: str, *, data: YAML_CONVERTER):
        """
        Store an embed from valid YAML on this server.
        """
        await self.store_embed(ctx, name, data)
        await ctx.tick()

    @embed_store.command(
        name="pastebin", aliases=["frompaste"], add_example_info=True, info_type="pastebin"
    )
    async def embed_store_pastebin(self, ctx, name: str, *, data: PASTEBIN_CONVERTER):
        """
        Store an embed from valid JSON or YAML from a pastebin link on this server.
        """
        await self.store_embed(ctx, name, data)
        await ctx.tick()

    @embed_store.command(
        name="fromfile",
        aliases=["fromjsonfile", "fromdatafile"],
        add_example_info=True,
    )
    async def embed_store_fromfile(self, ctx: commands.Context, name: str):
        """
        Store an embed from a valid JSON file on this server.
        """
        data = await self.get_file_from_message(ctx, file_types=("json", "txt"))
        e = await JSON_CONVERTER.convert(ctx, data)
        await self.store_embed(ctx, name, e)
        await ctx.tick()

    @embed_store.command(
        name="yamlfile",
        aliases=["fromyamlfile"],
        add_example_info=True,
        info_type="yaml",
    )
    async def embed_store_yamlfile(self, ctx: commands.Context, name: str):
        """
        Store an embed from a valid YAML file on this server.
        """
        data = await self.get_file_from_message(ctx, file_types=("yaml", "txt"))
        e = await YAML_CONVERTER.convert(ctx, data)
        await self.store_embed(ctx, name, e)
        await ctx.tick()

    @embed_store.command(
        name="message",
        aliases=["frommsg", "frommessage"],
        add_example_info=True,
        info_type="index",
    )
    async def embed_store_message(self, ctx, name: str, message: discord.Message, index: int = 0):
        """
        Store an embed from a message on this server.
        """
        embed = await self.get_embed_from_message(ctx, message, index)
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
        e = discord.Embed(color=color, title="Stored Embeds", description=description)
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
        e = discord.Embed(color=color, title="Stored Embeds", description=description)
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

    @global_store.command(name="json", aliases=["fromjson", "fromdata"], add_example_info=True)
    async def global_store_json(self, ctx, name: str, locked: bool, *, data: JSON_CONVERTER):
        """Store an embed from valid JSON globally.

        The `locked` argument specifies whether the embed should be locked to owners only."""
        await self.global_store_embed(ctx, name, data, locked)
        await ctx.tick()

    @global_store.command(
        name="pastebin", aliases=["frompaste"], add_example_info=True, info_type="pastebin"
    )
    async def global_store_pastebin(
        self, ctx, name: str, locked: bool, *, data: PASTEBIN_CONVERTER
    ):
        """Store an embed from valid JSON or YAML globally using a pastebin link.

        The `locked` argument specifies whether the embed should be locked to owners only."""
        await self.global_store_embed(ctx, name, data, locked)
        await ctx.tick()

    @global_store.command(
        name="fromfile",
        aliases=["fromjsonfile", "fromdatafile"],
        add_example_info=True,
    )
    async def global_store_fromfile(self, ctx: commands.Context, name: str, locked: bool):
        """
        Store an embed from a valid JSON file globally.

        The `locked` argument specifies whether the embed should be locked to owners only.
        """
        data = await self.get_file_from_message(ctx, file_types=("json", "txt"))
        e = await JSON_CONVERTER.convert(ctx, data)
        await self.global_store_embed(ctx, name, e, locked)
        await ctx.tick()

    @global_store.command(
        name="yamlfile",
        aliases=["fromyamlfile"],
        add_example_info=True,
        info_type="yaml",
    )
    async def global_store_yamlfile(self, ctx: commands.Context, name: str, locked: bool):
        """
        Store an embed from a valid YAML file globally.

        The `locked` argument specifies whether the embed should be locked to owners only.
        """
        data = await self.get_file_from_message(ctx, file_types=("yaml", "txt"))
        e = await YAML_CONVERTER.convert(ctx, data)
        await self.global_store_embed(ctx, name, e, locked)
        await ctx.tick()

    @global_store.command(
        name="message",
        aliases=["frommsg", "frommessage"],
        add_example_info=True,
        info_type="index",
    )
    async def global_store_message(
        self, ctx, name: str, message: discord.Message, locked: bool, index: int = 0
    ):
        """
        Store an embed from a message globally.

        The `locked` argument specifies whether the embed should be locked to owners only.
        """
        embed = await self.get_embed_from_message(ctx, message, index)
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

    async def webhook_send(self, ctx: commands.Context, **kwargs):
        cog = self.bot.get_cog("Webhook")
        try:
            await cog.send_to_channel(
                ctx.channel,
                ctx.me,
                ctx.author,
                ctx=ctx,
                **kwargs,
            )
        except discord.HTTPException as error:
            raise EmbedConversionError(ctx, "Embed Send Error", error) from error

    @commands.check(webhook_check)
    @commands.admin_or_permissions(manage_webhooks=True)
    @commands.bot_has_permissions(manage_webhooks=True)
    @embed.group(invoke_without_command=True, require_var_positional=True)
    async def webhook(self, ctx: commands.Context, *embeds: StoredEmbedConverter):
        """Send embeds through webhooks.

        Running this command with stored embed names will send up to 10 embeds through a webhook."""
        await self.webhook_send(
            ctx, embeds=[discord.Embed.from_dict(e["embed"]) for e in embeds[:10]]
        )

    @webhook.command(name="global", require_var_positional=True)
    async def webhook_global(self, ctx: commands.Context, *embeds: GlobalStoredEmbedConverter):
        """Send global embeds through webhooks.

        Running this command with global stored embed names will send up to 10 embeds through a webhook."""
        await self.webhook_send(
            ctx, embeds=[discord.Embed.from_dict(e["embed"]) for e in embeds[:10]]
        )

    @webhook.command(name="json", aliases=["fromjson", "fromdata"], add_example_info=True)
    async def webhook_json(self, ctx: commands.Context, *, embeds: ListStringToEmbed):
        """
        Send embeds through webhooks using JSON.
        """
        await self.webhook_send(ctx, embeds=embeds[:10])

    @webhook.command(name="yaml", aliases=["fromyaml"], add_example_info=True, info_type="yaml")
    async def webhook_yaml(
        self,
        ctx: commands.Context,
        *,
        embeds: ListStringToEmbed(conversion_type="yaml"),  # noqa: F821
    ):
        """
        Send embeds through webhooks using YAML.
        """
        await self.webhook_send(ctx, embeds=embeds[:10])

    @webhook.command(
        name="pastebin", aliases=["frompaste"], add_example_info=True, info_type="pastebin"
    )
    async def webhook_pastebin(
        self,
        ctx: commands.Context,
        *,
        embeds: PastebinConverterWebhook(conversion_type="yaml"),  # noqa: F821
    ):
        """
        Send embeds through webhooks using a pastebin link with valid YAML or JSON.
        """
        await self.webhook_send(ctx, embeds=embeds[:10])

    @webhook.command(name="message", aliases=["frommsg", "frommessage"])
    async def webhook_message(
        self, ctx: commands.Context, message: discord.Message, index: int = 0
    ):
        """
        Send embeds through webhooks.
        """
        embed = await self.get_embed_from_message(ctx, message, index)
        await self.webhook_send(ctx, embed=embed)

    @webhook.command(
        name="fromfile",
        aliases=["fromjsonfile", "fromdatafile"],
        add_example_info=True,
    )
    async def webhook_fromfile(self, ctx: commands.Context):
        """
        Send embeds through webhooks, using JSON files.
        """
        data = await self.get_file_from_message(ctx, file_types=("json", "txt"))
        embeds = await ListStringToEmbed().convert(ctx, data)
        await self.webhook_send(ctx, embeds=embeds[:10])

    @webhook.command(
        name="yamlfile",
        aliases=["fromyamlfile"],
        add_example_info=True,
        info_type="yaml",
    )
    async def webhook_yamlfile(self, ctx: commands.Context):
        """
        Send embeds through webhooks, using JSON files.
        """
        data = await self.get_file_from_message(ctx, file_types=("yaml", "txt"))
        embeds = await ListStringToEmbed(conversion_type="yaml").convert(ctx, data)
        await self.webhook_send(ctx, embeds=embeds[:10])

    async def store_embed(self, ctx: commands.Context, name: str, embed: discord.Embed):
        embed = embed.to_dict()
        async with self.config.guild(ctx.guild).embeds() as a:
            a[name] = {"author": ctx.author.id, "uses": 0, "embed": embed, "name": name}
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
            if data["locked"] is True and not await self.bot.is_owner(ctx.author):
                await ctx.send("This is not a stored embed.")
                return
        except KeyError:
            await ctx.send("This is not a stored embed.")
            return
        embed = discord.Embed.from_dict(embed)
        return embed, data["author"], data["uses"], data["locked"]

    async def cog_command_error(self, ctx: commands.Context, exc: Exception):
        if isinstance(exc, commands.CommandInvokeError):
            error = exc.original
            if isinstance(error, EmbedConversionError):
                await StringToEmbed.embed_convert_error(error.ctx, error.error_type, error.error)
            elif isinstance(error, EmbedUtilsException):
                ref = ctx.message.to_reference(fail_if_not_exists=False)
                await ctx.send(error, reference=ref)
            else:
                self.bot.dispatch("command_error", ctx, exc, unhandled_by_cog=True)
        else:
            self.bot.dispatch("command_error", ctx, exc, unhandled_by_cog=True)
