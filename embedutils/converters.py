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

import asyncio
import json
import re
from typing import Dict, List, Optional, Union

import discord
import yaml
from redbot.core import commands
from redbot.core.utils import menus

PASTEBIN_RE = re.compile(r"(?:https?://(?:www\.)?)?pastebin\.com/(?:raw/)?([a-zA-Z0-9]+)")


class StringToEmbed(commands.Converter):
    def __init__(
        self, *, conversion_type: str = "json", validate: bool = True, content: bool = False
    ):
        self.CONVERSION_TYPES = {
            "json": self.load_from_json,
            "yaml": self.load_from_yaml,
        }

        self.validate = validate
        self.conversion_type = conversion_type.lower()
        self.allow_content = content
        try:
            self.converter = self.CONVERSION_TYPES[self.conversion_type]
        except KeyError as exc:
            raise ValueError(
                f"{conversion_type} is not a valid conversion type for Embed conversion."
            ) from exc

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Embed:
        data = argument.strip("`")
        data = await self.converter(ctx, data)
        content = self.get_content(data)

        if data.get("embed"):
            data = data["embed"]
        elif data.get("embeds"):
            data = data.get("embeds")[0]
        self.check_data_type(ctx, data)

        fields = await self.create_embed(ctx, data, content=content)
        content = fields["content"]
        embed = fields["embed"]
        if self.validate:
            await self.validate_embed(ctx, embed, content=content)
        return embed

    def check_data_type(self, ctx: commands.Context, data, *, data_type=dict):
        if not isinstance(data, data_type):
            raise commands.BadArgument(
                f"This doesn't seem to be properly formatted embed {self.conversion_type.upper()}. "
                f"Refer to the link on `{ctx.clean_prefix}help {ctx.command.qualified_name}`."
            )

    async def load_from_json(self, ctx: commands.Context, data: str, **kwargs) -> dict:
        try:
            data = json.loads(data)
        except json.decoder.JSONDecodeError as error:
            await self.embed_convert_error(ctx, "JSON Parse Error", error)
        self.check_data_type(ctx, data, **kwargs)
        return data

    async def load_from_yaml(self, ctx: commands.Context, data: str, **kwargs) -> dict:
        try:
            data = yaml.safe_load(data)
        except Exception as error:
            await self.embed_convert_error(ctx, "YAML Parse Error", error)
        self.check_data_type(ctx, data, **kwargs)
        return data

    def get_content(self, data: dict, *, content: str = None) -> Optional[str]:
        content = data.pop("content", content)
        if content is not None and not self.allow_content:
            raise commands.BadArgument("The `content` field is not supported for this command.")
        return content

    async def create_embed(
        self, ctx: commands.Context, data: dict, *, content: str = None
    ) -> Dict[str, Union[discord.Embed, str]]:
        content = self.get_content(data, content=content)

        if timestamp := data.get("timestamp"):
            data["timestamp"] = timestamp.strip("Z")
        try:
            e = discord.Embed.from_dict(data)
            length = len(e)
        except Exception as error:
            await self.embed_convert_error(ctx, "Embed Parse Error", error)

        # Embed.__len__ may error which is why it is included in the try/except
        if length > 6000:
            raise commands.BadArgument(
                f"Embed size exceeds Discord limit of 6000 characters ({length})."
            )
        return {"embed": e, "content": content}

    async def validate_embed(
        self, ctx: commands.Context, embed: discord.Embed, *, content: str = None
    ):
        try:
            await ctx.channel.send(content, embed=embed)  # ignore tips/monkeypatch cogs
        except discord.errors.HTTPException as error:
            await self.embed_convert_error(ctx, "Embed Send Error", error)

    @staticmethod
    async def embed_convert_error(ctx: commands.Context, error_type: str, error: Exception):
        embed = discord.Embed(
            color=await ctx.embed_color(),
            title=f"{error_type}: `{type(error).__name__}`",
            description=f"```py\n{error}\n```",
        )
        embed.set_footer(
            text=f"Use `{ctx.prefix}help {ctx.command.qualified_name}` to see an example"
        )
        asyncio.create_task(menus.menu(ctx, [embed], {"❌": menus.close_menu}))
        raise commands.CheckFailure()


class ListStringToEmbed(StringToEmbed):
    async def convert(self, ctx: commands.Context, argument: str) -> List[discord.Embed]:
        data = argument.strip("`")
        data = await self.converter(ctx, data, data_type=(dict, list))

        if isinstance(data, list):
            pass
        elif data.get("embed"):
            data = [data["embed"]]
        elif data.get("embeds"):
            data = data.get("embeds")
            if isinstance(data, dict):
                data = list(data.values())
        else:
            data = [data]
        self.check_data_type(ctx, data, data_type=list)

        embeds = []
        for embed_data in data:
            fields = await self.create_embed(ctx, embed_data)
            embed = fields["embed"]
            embeds.append(embed)
        if embeds:
            return embeds
        else:
            raise commands.BadArgument("Failed to convert input into embeds.")


class EmbedNotFound(commands.BadArgument):
    def __init__(self, name: str, *, is_global: bool = False):
        embed = "Global embed" if is_global else "Embed"
        super().__init__(f'{embed} "{name}" not found.')


class StoredEmbedConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, name: str) -> dict:
        cog = ctx.bot.get_cog("EmbedUtils")
        data = await cog.config.guild(ctx.guild).embeds()
        embed = data.get(name)
        if not embed:
            raise EmbedNotFound(name)
        embed.update(name=name)
        return embed


class GlobalStoredEmbedConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, name: str) -> dict:
        cog = ctx.bot.get_cog("EmbedUtils")
        data = await cog.config.embeds()
        embed = data.get(name)
        if not embed:
            raise EmbedNotFound(name, is_global=True)
        can_view = await ctx.bot.is_owner(ctx.author) or not embed.get("locked")
        if embed and can_view:
            embed.update(name=name)
            return embed
        raise EmbedNotFound(name, is_global=True)


class MyMessageConverter(commands.MessageConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Message:
        message = await super().convert(ctx, argument)
        if message.author.id != ctx.me.id:
            raise commands.BadArgument("That is not a message sent by me.")
        elif not message.channel.permissions_for(ctx.me).send_messages:
            raise commands.BadArgument(
                f"I do not have permissions to send/edit messages in {message.channel.mention}."
            )
        return message


class MessageableChannel(commands.TextChannelConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.TextChannel:
        channel = await super().convert(ctx, argument)
        my_perms = channel.permissions_for(ctx.me)
        if not (my_perms.send_messages and my_perms.embed_links):
            raise commands.BadArgument(
                f"I do not have permissions to send embeds in {channel.mention}."
            )
        author_perms = channel.permissions_for(ctx.author)
        if not (author_perms.send_messages and author_perms.embed_links):
            raise commands.BadArgument(
                f"You do not have permissions to send embeds in {channel.mention}."
            )
        return channel


class PastebinMixin:
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        match = PASTEBIN_RE.match(argument)
        if not match:
            raise commands.BadArgument(f"`{argument}` is not a valid Pastebin link.")
        paste_id = match.group(1)
        async with ctx.cog.session.get(f"https://pastebin.com/raw/{paste_id}") as resp:
            if resp.status != 200:
                raise commands.BadArgument(f"`{argument}` is not a valid Pastebin link.")
            embed_data = await resp.text()
        return await super().convert(ctx, embed_data)


class PastebinConverter(PastebinMixin, StringToEmbed):
    ...


class PastebinConverterWebhook(PastebinMixin, ListStringToEmbed):
    ...
