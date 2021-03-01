from typing import List
import discord
from redbot.core import commands
from redbot.core.commands import Converter, BadArgument, CheckFailure, MessageConverter, TextChannelConverter
import json
from redbot.core.utils import menus
import asyncio


class StringToEmbed(Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Embed:
        data = argument.strip("`")
        try:
            data = json.loads(data)
        except json.decoder.JSONDecodeError as error:
            await self.embed_convert_error(ctx, "JSON Parse Error", error)
            return
        if data.get("embed"):
            data = data["embed"]
        elif data.get("embeds"):
            data = data.get("embeds")[0]
        if not isinstance(data, dict):
            raise BadArgument(
                "This doesn't seem to be properly formatted embed"
                f" JSON. Refer to the link on `{ctx.clean_prefix}help {ctx.command.qualified_name}`."
            )
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
        asyncio.create_task(menus.menu(ctx, [embed], {"❌": menus.close_menu}))
        raise CheckFailure


class ListStringToEmbed(StringToEmbed):
    async def convert(self, ctx: commands.Context, argument: str) -> List[discord.Embed]:
        data = argument.strip("`")
        try:
            data = json.loads(data)
        except json.decoder.JSONDecodeError as error:
            await self.embed_convert_error(ctx, "JSON Parse Error", error)
            return
        if data.get("embed"):
            data = [data["embed"]]
        elif data.get("embeds"):
            data = data.get("embeds")
        else:
            data = [data]
        embeds = []
        for embed_data in data:
            if embed_data.get("timestamp"):
                embed_data["timestamp"] = embed_data["timestamp"].strip("Z")
            try:
                e = discord.Embed.from_dict(embed_data)
            except Exception as error:
                await self.embed_convert_error(ctx, "Embed Parse Error", error)
                return
            else:
                embeds.append(e)
        if embeds:
            return embeds
        else:
            raise BadArgument


class StoredEmbedConverter(Converter):
    async def convert(self, ctx: commands.Context, name: str) -> dict:
        cog = ctx.bot.get_cog("EmbedUtils")
        data = await cog.config.guild(ctx.guild).embeds()
        embed = data.get(name)
        if embed:
            embed.update(name=name)
            return embed
        else:
            raise BadArgument(f'Embed "{name}" not found.')


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
