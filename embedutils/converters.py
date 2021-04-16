import asyncio
import json
from typing import List, Dict, Union, Optional

import discord
from redbot.core import commands
from redbot.core.commands import (
    Converter,
    BadArgument,
    CheckFailure,
    MessageConverter,
    TextChannelConverter,
)
from redbot.core.utils import menus
import yaml


class StringToEmbed(Converter):
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
            raise BadArgument(
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
            raise BadArgument("The `content` field is not supported for this command.")
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
            if length > 6000:
                raise BadArgument(
                    f"Embed size exceeds Discord limit of 6000 characters ({length})."
                )
        except BadArgument:
            raise
        except Exception as error:
            await self.embed_convert_error(ctx, "Embed Parse Error", error)
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
        raise CheckFailure


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
            raise BadArgument


class StoredEmbedConverter(Converter):
    async def convert(self, ctx: commands.Context, name: str) -> dict:
        cog = ctx.bot.get_cog("EmbedUtils")
        data = await cog.config.guild(ctx.guild).embeds()
        embed = data.get(name)
        if not embed:
            raise BadArgument(f'Embed "{name}" not found.')

        embed.update(name=name)
        return embed


class GlobalStoredEmbedConverter(Converter):
    async def convert(self, ctx: commands.Context, name: str) -> dict:
        cog = ctx.bot.get_cog("EmbedUtils")
        data = await cog.config.embeds()
        embed = data.get(name)
        can_view = await ctx.bot.is_owner(ctx.author) or not embed.get("locked")
        if embed and can_view:
            embed.update(name=name)
            return embed
        else:
            raise BadArgument(f'Global embed "{name}" not found.')


class MyMessageConverter(MessageConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Message:
        message = await super().convert(ctx, argument)
        if message.author.id != ctx.me.id:
            raise BadArgument(f"That is not a message sent by me.")
        elif not message.channel.permissions_for(ctx.me).send_messages:
            raise BadArgument(
                f"I do not have permissions to send/edit messages in {message.channel.mention}."
            )
        return message


class MessageableChannel(TextChannelConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.TextChannel:
        channel = await super().convert(ctx, argument)
        my_perms = channel.permissions_for(ctx.me)
        if not (my_perms.send_messages and my_perms.embed_links):
            raise BadArgument(f"I do not have permissions to send embeds in {channel.mention}.")
        author_perms = channel.permissions_for(ctx.author)
        if not (author_perms.send_messages and author_perms.embed_links):
            raise BadArgument(f"You do not have permissions to send embeds in {channel.mention}.")
        return channel
