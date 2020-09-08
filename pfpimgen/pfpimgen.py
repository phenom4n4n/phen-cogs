from typing import Literal
from io import BytesIO
from PIL import Image
import functools
import asyncio

import discord
from redbot.core import commands, checks
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.data_manager import bundled_data_path

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class PfpImgen(commands.Cog):
    """
    Make images from avatars!
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=82345678897346,
            force_registration=True,
        )

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        return

    @checks.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.command(aliases=["catgirl"])
    async def neko(self, ctx, *, member: discord.Member = None):
        """Make a neko avatar..."""
        if not member:
            member = ctx.author
        
        async with ctx.typing():
            avatar = await self.get_avatar(member, 156)
            task = functools.partial(self.gen_neko, ctx, avatar)
            task = self.bot.loop.run_in_executor(None, task)
            try:
                neko = await asyncio.wait_for(task, timeout=60)
            except asyncio.TimeoutError:
                return await ctx.send("An error occurred while generating this image. Try again later.")
        await ctx.send(file=discord.File(neko, "neko.png"))
        
    @checks.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.command()
    async def bonk(self, ctx, *, member: discord.Member = None):
        """Bonk! Go to horny jail."""
        await ctx.trigger_typing()
        bonker = False
        if member:
            bonker = ctx.author
        else:
            member = ctx.author

        async with ctx.typing():
            victim_avatar = await self.get_avatar(member, 256)
            if bonker:
                bonker_avatar = await self.get_avatar(bonker, 223)
                task = functools.partial(self.gen_bonk, ctx, victim_avatar, bonker_avatar)
            else:
                task = functools.partial(self.gen_bonk, ctx, victim_avatar)
            task = self.bot.loop.run_in_executor(None, task)
            try:
                bonk = await asyncio.wait_for(task, timeout=60)
            except asyncio.TimeoutError:
                return await ctx.send("An error occurred while generating this image. Try again later.")
        await ctx.send(file=discord.File(bonk, "bonk.png"))

    @checks.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.command()
    async def simp(self, ctx, *, member: discord.Member = None):
        """You are now a simp."""
        if not member:
            member = ctx.author
        async with ctx.typing():
            avatar = await self.get_avatar(member, 136)
            task = functools.partial(self.gen_simp, ctx, avatar)
            task = self.bot.loop.run_in_executor(None, task)
            try:
                bonk = await asyncio.wait_for(task, timeout=60)
            except asyncio.TimeoutError:
                return await ctx.send("An error occurred while generating this image. Try again later.")
        await ctx.send(file=discord.File(bonk, "simp.png"))

    async def get_avatar(self, member: discord.Member, size: int):
        avatar = BytesIO()
        await member.avatar_url.save(avatar, seek_begin=True)
        avatar = Image.open(avatar).convert("RGBA")
        avatar = avatar.resize((size, size), Image.ANTIALIAS)
        return avatar

    def gen_neko(self, ctx, member_avatar):
        # base canvas
        im = Image.new("RGBA", (500, 750), None)
        #neko = Image.open(f"{bundled_data_path(ctx.cog)}/neko/neko.png", mode="r").convert("RGBA")
        nekomask = Image.open(f"{bundled_data_path(ctx.cog)}/neko/nekomask.png", mode="r").convert("RGBA")
        #im.paste(neko, (0, 0), neko)

        # pasting the pfp
        im.paste(member_avatar, (149, 122), member_avatar)
        im.paste(nekomask, (0, 0), nekomask)

        fp = BytesIO()
        im.save(fp, "PNG")
        fp.seek(0)
        return fp

    def gen_bonk(self, ctx, victim_avatar, bonker_avatar=None):
        # base canvas
        im = Image.open(f"{bundled_data_path(ctx.cog)}/bonk/bonkbase.png", mode="r").convert("RGBA")

        # pasting the victim
        victim_avatar = victim_avatar.rotate(angle=10)
        im.paste(victim_avatar, (650, 225), victim_avatar)
        
        # pasting the bonker
        if bonker_avatar:
            im.paste(bonker_avatar, (206, 69), bonker_avatar)

        # pasting the bat
        bonkbat = Image.open(f"{bundled_data_path(ctx.cog)}/bonk/bonkbat.png", mode="r").convert("RGBA")
        im.paste(bonkbat, (452, 132), bonkbat)

        fp = BytesIO()
        im.save(fp, "PNG")
        fp.seek(0)
        return fp

    def gen_simp(self, ctx, member_avatar):
        # base canvas
        im = Image.new("RGBA", (500, 319), None)
        card = Image.open(f"{bundled_data_path(ctx.cog)}/simp/simp.png", mode="r").convert("RGBA")

        # pasting the pfp
        member_avatar = member_avatar.rotate(angle=3, expand=True)
        im.paste(member_avatar, (73, 105))
        
        # pasting the card
        im.paste(card, (0, 0), card)

        fp = BytesIO()
        im.save(fp, "PNG")
        fp.seek(0)
        return fp