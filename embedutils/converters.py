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
            color=await ctx.bot.get_embed_color(ctx),
            title=error_type,
            description=f"```py\n{error}\n```",
        )
        embed.set_footer(
            text=f"Use `{ctx.prefix}help {ctx.command.qualified_name}` to see an example"
        )
        emoji = ctx.bot.get_emoji(736038541364297738)
        if not emoji:
            emoji = "❌"
        asyncio.create_task(menus.menu(ctx, [embed], {emoji: menus.close_menu}))
        raise CheckFailure