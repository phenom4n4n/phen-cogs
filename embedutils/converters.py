from typing import List
import discord
from redbot.core import commands
from redbot.core.commands import Converter, BadArgument, CheckFailure
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
        asyncio.create_task(menus.menu(ctx, [embed], {emoji: menus.close_menu}))
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
