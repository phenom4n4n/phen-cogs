from typing import Literal, Optional
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
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
    @commands.cooldown(1, 10, commands.BucketType.user)
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
                return await ctx.send(
                    "An error occurred while generating this image. Try again later."
                )
        await ctx.send(file=discord.File(neko, "neko.png"))

    @checks.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
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
                return await ctx.send(
                    "An error occurred while generating this image. Try again later."
                )
        await ctx.send(file=discord.File(bonk, "bonk.png"))

    @checks.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
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
                simp = await asyncio.wait_for(task, timeout=60)
            except asyncio.TimeoutError:
                return await ctx.send(
                    "An error occurred while generating this image. Try again later."
                )
        await ctx.send(file=discord.File(simp, "simp.png"))

    @checks.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command()
    async def banner(self, ctx, *, member: discord.Member = None):
        """Banner"""
        if not member:
            member = ctx.author
        async with ctx.typing():
            avatar = await self.get_avatar(member, 200)
            task = functools.partial(self.gen_banner, ctx, avatar, member.color)
            task = self.bot.loop.run_in_executor(None, task)
            try:
                banner = await asyncio.wait_for(task, timeout=60)
            except asyncio.TimeoutError:
                return await ctx.send(
                    "An error occurred while generating this image. Try again later."
                )
        await ctx.send(file=discord.File(banner, "banner.png"))

    @checks.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command()
    async def nickel(
        self,
        ctx,
        member: Optional[discord.Member] = None,
        *,
        text: commands.clean_content(fix_channel_mentions=True),
    ):
        """If I had a nickel for everytime someone ran this command..

        I'd probably have a lot."""
        text = " ".join(text.split())
        if not member:
            member = ctx.author
        async with ctx.typing():
            avatar = await self.get_avatar(member, 182)
            task = functools.partial(self.gen_nickel, ctx, avatar, text[:29])
            task = self.bot.loop.run_in_executor(None, task)
            try:
                nickel = await asyncio.wait_for(task, timeout=60)
            except asyncio.TimeoutError:
                return await ctx.send(
                    "An error occurred while generating this image. Try again later."
                )
        await ctx.send(file=discord.File(nickel, "nickel.png"))

    @checks.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command()
    async def shutup(
        self,
        ctx,
        member: Optional[discord.Member] = None,
        *,
        text: commands.clean_content(fix_channel_mentions=True),
    ):
        """Tell someone to shut up"""
        if not member:
            member = ctx.author
        async with ctx.typing():
            avatar = await self.get_avatar(member, 140)
            task = functools.partial(self.gen_shut, ctx, avatar, text)
            task = self.bot.loop.run_in_executor(None, task)
            try:
                shut = await asyncio.wait_for(task, timeout=60)
            except asyncio.TimeoutError:
                return await ctx.send(
                    "An error occurred while generating this image. Try again later."
                )
        await ctx.send(file=discord.File(shut, "shut.png"))

    async def get_avatar(self, member: discord.User, size: int):
        avatar = BytesIO()
        await member.avatar_url.save(avatar, seek_begin=True)
        avatar = Image.open(avatar).convert("RGBA")
        avatar = avatar.resize((size, size), Image.ANTIALIAS)
        return avatar

    def gen_neko(self, ctx, member_avatar):
        # base canvas
        im = Image.new("RGBA", (500, 750), None)
        # neko = Image.open(f"{bundled_data_path(self)}/neko/neko.png", mode="r").convert("RGBA")
        nekomask = Image.open(f"{bundled_data_path(self)}/neko/nekomask.png", mode="r").convert(
            "RGBA"
        )
        # im.paste(neko, (0, 0), neko)

        # pasting the pfp
        im.paste(member_avatar, (149, 122), member_avatar)
        im.paste(nekomask, (0, 0), nekomask)

        fp = BytesIO()
        im.save(fp, "PNG")
        fp.seek(0)
        return fp

    def gen_bonk(self, ctx, victim_avatar, bonker_avatar=None):
        # base canvas
        im = Image.open(f"{bundled_data_path(self)}/bonk/bonkbase.png", mode="r").convert(
            "RGBA"
        )

        # pasting the victim
        victim_avatar = victim_avatar.rotate(angle=10, resample=Image.BILINEAR)
        im.paste(victim_avatar, (650, 225), victim_avatar)

        # pasting the bonker
        if bonker_avatar:
            im.paste(bonker_avatar, (206, 69), bonker_avatar)

        # pasting the bat
        bonkbat = Image.open(f"{bundled_data_path(self)}/bonk/bonkbat.png", mode="r").convert(
            "RGBA"
        )
        im.paste(bonkbat, (452, 132), bonkbat)

        fp = BytesIO()
        im.save(fp, "PNG")
        fp.seek(0)
        return fp

    def gen_simp(self, ctx, member_avatar):
        # base canvas
        im = Image.new("RGBA", (500, 319), None)
        card = Image.open(f"{bundled_data_path(self)}/simp/simp.png", mode="r").convert("RGBA")

        # pasting the pfp
        member_avatar = member_avatar.rotate(angle=3, resample=Image.BILINEAR, expand=True)
        im.paste(member_avatar, (73, 105))

        # pasting the card
        im.paste(card, (0, 0), card)

        fp = BytesIO()
        im.save(fp, "PNG")
        fp.seek(0)
        return fp

    def gen_banner(self, ctx, member_avatar, color: discord.Color):
        im = Image.new("RGBA", (489, 481), color.to_rgb())
        comic = Image.open(f"{bundled_data_path(self)}/banner/banner.png", mode="r").convert(
            "RGBA"
        )

        # 2nd slide
        av = member_avatar.rotate(angle=7, resample=Image.BILINEAR, expand=True)
        av = av.resize((90, 90), Image.LANCZOS)
        im.paste(av, (448, 38), av)

        # 3rd slide
        av2 = member_avatar.rotate(angle=7, resample=Image.BILINEAR, expand=True)
        av2 = av2.resize((122, 124), Image.LANCZOS)
        im.paste(av2, (47, 271), av2)

        # 4th slide
        av2 = member_avatar.rotate(angle=26, resample=Image.BILINEAR, expand=True)
        av2 = av2.resize((147, 148), Image.LANCZOS)
        im.paste(av2, (325, 233), av2)

        # cover = Image.open(f"{bundled_data_path(self)}/banner/bannercover.png", mode="r").convert("RGBA")
        # im.paste(cover, (240, 159), cover)
        im.paste(comic, (0, 0), comic)

        fp = BytesIO()
        im.save(fp, "PNG")
        fp.seek(0)
        return fp

    def gen_nickel(self, ctx, member_avatar, text: str):
        # base canvas
        im = Image.open(f"{bundled_data_path(self)}/nickel/nickel.png", mode="r").convert(
            "RGBA"
        )

        # avatars
        im.paste(member_avatar, (69, 70), member_avatar)
        im.paste(member_avatar, (69, 407), member_avatar)
        im.paste(member_avatar, (104, 758), member_avatar)

        # text
        font = ImageFont.truetype(f"{bundled_data_path(self)}/arial.ttf", 30)
        canvas = ImageDraw.Draw(im)
        text_width, text_height = canvas.textsize(text, font, stroke_width=2)
        canvas.text(
            ((im.width - text_width) / 2, 285),
            text,
            font=font,
            fill=(206, 194, 114),
            align="center",
            stroke_width=2,
            stroke_fill=(0, 0, 0),
        )

        fp = BytesIO()
        im.save(fp, "PNG")
        fp.seek(0)
        return fp

    def circle_avatar(self, avatar):
        mask = Image.new("L", avatar.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + avatar.size, fill=255)
        avatar.putalpha(mask)
        return avatar

    def gen_shut(self, ctx, member_avatar, text: str):
        # base canvas
        im = Image.open(f"{bundled_data_path(self)}/shutup/shutup.png", mode="r").convert(
            "RGBA"
        )

        # avatars
        circle_main = self.circle_avatar(member_avatar).rotate(
            angle=57, resample=Image.BILINEAR, expand=True
        )
        im.paste(circle_main, (84, 207), circle_main)
        im.paste(circle_main, (42, 864), circle_main)

        # text
        font = ImageFont.truetype(f"{bundled_data_path(self)}/arial.ttf", 25)
        canvas = ImageDraw.Draw(im)
        text_width, text_height = canvas.textsize(text, font, stroke_width=2)
        canvas.multiline_text(
            (((im.width - text_width) / 2) + 25, 75),
            text,
            font=font,
            fill=(255, 255, 255),
            align="center",
            spacing=2,
            stroke_width=2,
            stroke_fill=(0, 0, 0),
        )

        fp = BytesIO()
        im.save(fp, "PNG")
        fp.seek(0)
        return fp
