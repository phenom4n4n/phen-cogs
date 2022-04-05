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
import functools
from io import BytesIO
from typing import Literal, Optional

import aiohttp
import discord
from PIL import Image, ImageDraw, ImageFont
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.data_manager import bundled_data_path
from redbot.core.utils.chat_formatting import pagify

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

from .converters import FuzzyMember


class PfpImgen(commands.Cog):
    """
    Make images from avatars!
    """

    __version__ = "1.1.1"

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=82345678897346,
            force_registration=True,
        )
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        await self.session.close()

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        return

    @commands.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(aliases=["catgirl"], cooldown_after_parsing=True)
    async def neko(self, ctx, *, member: FuzzyMember = None):
        """Make a neko avatar..."""
        if not member:
            member = ctx.author

        async with ctx.typing():
            avatar = await self.get_avatar(member)
            task = functools.partial(self.gen_neko, ctx, avatar)
            image = await self.generate_image(task)
        if isinstance(image, str):
            await ctx.send(image)
        else:
            await ctx.send(file=image)

    @commands.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(cooldown_after_parsing=True)
    async def bonk(self, ctx, *, member: FuzzyMember = None):
        """Bonk! Go to horny jail."""
        await ctx.trigger_typing()
        bonker = False
        if member:
            bonker = ctx.author
        else:
            member = ctx.author

        async with ctx.typing():
            victim_avatar = await self.get_avatar(member)
            if bonker:
                bonker_avatar = await self.get_avatar(bonker)
                task = functools.partial(self.gen_bonk, ctx, victim_avatar, bonker_avatar)
            else:
                task = functools.partial(self.gen_bonk, ctx, victim_avatar)
            image = await self.generate_image(task)
        if isinstance(image, str):
            await ctx.send(image)
        else:
            await ctx.send(file=image)

    @commands.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(cooldown_after_parsing=True)
    async def simp(self, ctx, *, member: FuzzyMember = None):
        """You are now a simp."""
        if not member:
            member = ctx.author
        async with ctx.typing():
            avatar = await self.get_avatar(member)
            task = functools.partial(self.gen_simp, ctx, avatar)
            image = await self.generate_image(task)
        if isinstance(image, str):
            await ctx.send(image)
        else:
            await ctx.send(file=image)

    @commands.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(cooldown_after_parsing=True)
    async def banner(self, ctx, *, member: FuzzyMember = None):
        """Banner"""
        if not member:
            member = ctx.author
        async with ctx.typing():
            avatar = await self.get_avatar(member)
            task = functools.partial(self.gen_banner, ctx, avatar, member.color)
            image = await self.generate_image(task)
        if isinstance(image, str):
            await ctx.send(image)
        else:
            await ctx.send(file=image)

    @commands.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(cooldown_after_parsing=True)
    async def nickel(
        self,
        ctx,
        member: Optional[FuzzyMember] = None,
        *,
        text: commands.clean_content(fix_channel_mentions=True),
    ):
        """If I had a nickel for everytime someone ran this command..

        I'd probably have a lot."""
        text = " ".join(text.split())
        if not member:
            member = ctx.author
        async with ctx.typing():
            avatar = await self.get_avatar(member)
            task = functools.partial(self.gen_nickel, ctx, avatar, text[:29])
            image = await self.generate_image(task)
        if isinstance(image, str):
            await ctx.send(image)
        else:
            await ctx.send(file=image)

    @commands.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(cooldown_after_parsing=True)
    async def stoptalking(
        self,
        ctx,
        member: Optional[FuzzyMember] = None,
        *,
        text: commands.clean_content(fix_channel_mentions=True),
    ):
        """Tell someone to stop blabbering away"""
        text = " ".join(text.split())
        if not member:
            member = ctx.author
        async with ctx.typing():
            avatar = await self.get_avatar(member)
            task = functools.partial(self.gen_stop, ctx, avatar, text)
            image = await self.generate_image(task)
        if isinstance(image, str):
            await ctx.send(image)
        else:
            await ctx.send(file=image)

    @commands.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(cooldown_after_parsing=True)
    async def horny(self, ctx, *, member: FuzzyMember = None):
        """Assign someone a horny license."""
        member = member or ctx.author
        async with ctx.typing():
            avatar = await self.get_avatar(member)
            task = functools.partial(self.gen_horny, avatar)
            image = await self.generate_image(task)
        if isinstance(image, str):
            await ctx.send(image)
        else:
            await ctx.send(file=image)

    @commands.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(cooldown_after_parsing=True)
    async def shutup(
        self,
        ctx,
        member: Optional[FuzzyMember] = None,
        *,
        text: commands.clean_content(fix_channel_mentions=True),
    ):
        """Will you shutup, man"""
        text = " ".join(text.split())
        if not member:
            biden = None
            member = ctx.author
        else:
            biden = ctx.author
        async with ctx.typing():
            trump = await self.get_avatar(member)
            if biden:
                biden = await self.get_avatar(biden)
            task = functools.partial(self.gen_shut, ctx, trump, text, biden_avatar=biden)
            image = await self.generate_image(task)
        if isinstance(image, str):
            await ctx.send(image)
        else:
            await ctx.send(file=image)

    @commands.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(cooldown_after_parsing=True)
    async def petpet(self, ctx: commands.Context, member: FuzzyMember = None):
        """petpet someone"""
        member = member or ctx.author
        async with ctx.typing():
            params = {"avatar": str(member.avatar_url_as(format="png"))}
            url = "https://api.obamabot.ml/v1/image/petpet"
            async with self.session.get(url, params=params) as resp:
                if resp.status != 200:
                    return await ctx.send(
                        "An error occurred while generating this image. Try again later."
                    )
                image = await resp.read()
            fp = BytesIO(image)
            fp.seek(0)
            file = discord.File(fp, "petpet.gif")
            fp.close()
        await ctx.send(file=file)

    async def generate_image(self, task: functools.partial):
        task = self.bot.loop.run_in_executor(None, task)
        try:
            image = await asyncio.wait_for(task, timeout=60)
        except asyncio.TimeoutError:
            return "An error occurred while generating this image. Try again later."
        else:
            return image

    async def get_avatar(self, member: discord.abc.User):
        avatar = BytesIO()
        display_avatar: discord.Asset = member.display_avatar.replace(static_format="png")
        await display_avatar.save(avatar, seek_begin=True)
        return avatar

    @staticmethod
    def bytes_to_image(image: BytesIO, size: int):
        image = Image.open(image).convert("RGBA")
        image = image.resize((size, size), Image.ANTIALIAS)
        return image

    def gen_neko(self, ctx, member_avatar):
        member_avatar = self.bytes_to_image(member_avatar, 156)
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
        nekomask.close()
        member_avatar.close()

        fp = BytesIO()
        im.save(fp, "PNG")
        fp.seek(0)
        im.close()
        _file = discord.File(fp, "neko.png")
        fp.close()
        return _file

    def gen_bonk(self, ctx, victim_avatar, bonker_avatar=None):
        # base canvas
        im = Image.open(f"{bundled_data_path(self)}/bonk/bonkbase.png", mode="r").convert("RGBA")

        # pasting the victim
        victim_avatar = self.bytes_to_image(victim_avatar, 256)
        victim_avatar = victim_avatar.rotate(angle=10, resample=Image.BILINEAR)
        im.paste(victim_avatar, (650, 225), victim_avatar)
        victim_avatar.close()

        # pasting the bonker
        if bonker_avatar:
            bonker_avatar = self.bytes_to_image(bonker_avatar, 223)
            im.paste(bonker_avatar, (206, 69), bonker_avatar)
            bonker_avatar.close()

        # pasting the bat
        bonkbat = Image.open(f"{bundled_data_path(self)}/bonk/bonkbat.png", mode="r").convert(
            "RGBA"
        )
        im.paste(bonkbat, (452, 132), bonkbat)
        bonkbat.close()

        fp = BytesIO()
        im.save(fp, "PNG")
        fp.seek(0)
        im.close()
        _file = discord.File(fp, "bonk.png")
        fp.close()
        return _file

    def gen_simp(self, ctx, member_avatar):
        member_avatar = self.bytes_to_image(member_avatar, 136)
        # base canvas
        im = Image.new("RGBA", (500, 319), None)
        card = Image.open(f"{bundled_data_path(self)}/simp/simp.png", mode="r").convert("RGBA")

        # pasting the pfp
        member_avatar = member_avatar.rotate(angle=3, resample=Image.BILINEAR, expand=True)
        im.paste(member_avatar, (73, 105))
        member_avatar.close()

        # pasting the card
        im.paste(card, (0, 0), card)
        card.close()

        fp = BytesIO()
        im.save(fp, "PNG")
        fp.seek(0)
        im.close()
        _file = discord.File(fp, "simp.png")
        fp.close()
        return _file

    def gen_banner(self, ctx, member_avatar, color: discord.Color):
        im = Image.new("RGBA", (489, 481), color.to_rgb())
        comic = Image.open(f"{bundled_data_path(self)}/banner/banner.png", mode="r").convert(
            "RGBA"
        )
        member_avatar = self.bytes_to_image(member_avatar, 200)

        # 2nd slide
        av = member_avatar.rotate(angle=7, resample=Image.BILINEAR, expand=True)
        av = av.resize((90, 90), Image.LANCZOS)
        im.paste(av, (448, 38), av)

        # 3rd slide
        av2 = member_avatar.rotate(angle=7, resample=Image.BILINEAR, expand=True)
        av2 = av2.resize((122, 124), Image.LANCZOS)
        im.paste(av2, (47, 271), av2)

        # 4th slide
        av3 = member_avatar.rotate(angle=26, resample=Image.BILINEAR, expand=True)
        av3 = av3.resize((147, 148), Image.LANCZOS)
        im.paste(av2, (345, 233), av2)

        av.close()
        av2.close()
        av3.close()
        member_avatar.close()

        # cover = Image.open(f"{bundled_data_path(self)}/banner/bannercover.png", mode="r").convert("RGBA")
        # im.paste(cover, (240, 159), cover)
        im.paste(comic, (0, 0), comic)

        fp = BytesIO()
        im.save(fp, "PNG")
        fp.seek(0)
        im.close()
        _file = discord.File(fp, "banner.png")
        fp.close()
        return _file

    def gen_nickel(self, ctx, member_avatar, text: str):
        member_avatar = self.bytes_to_image(member_avatar, 182)
        # base canvas
        im = Image.open(f"{bundled_data_path(self)}/nickel/nickel.png", mode="r").convert("RGBA")

        # avatars
        im.paste(member_avatar, (69, 70), member_avatar)
        im.paste(member_avatar, (69, 407), member_avatar)
        im.paste(member_avatar, (104, 758), member_avatar)
        member_avatar.close()

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
        im.close()
        _file = discord.File(fp, "nickel.png")
        fp.close()
        return _file

    def circle_avatar(self, avatar):
        mask = Image.new("L", avatar.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + avatar.size, fill=255)
        avatar.putalpha(mask)
        return avatar

    def gen_stop(self, ctx, member_avatar, text: str):
        member_avatar = self.bytes_to_image(member_avatar, 140)
        # base canvas
        im = Image.open(f"{bundled_data_path(self)}/stop/stop.png", mode="r").convert("RGBA")

        # avatars
        circle_main = self.circle_avatar(member_avatar).rotate(
            angle=57, resample=Image.BILINEAR, expand=True
        )
        im.paste(circle_main, (84, 207), circle_main)
        im.paste(circle_main, (42, 864), circle_main)
        member_avatar.close()
        circle_main.close()

        # text
        font = ImageFont.truetype(f"{bundled_data_path(self)}/arial.ttf", 25)
        canvas = ImageDraw.Draw(im)
        y = 70
        pages = list(pagify(text, [" "], page_length=30))[:4]
        for page in pages:
            text_width, text_height = canvas.textsize(page, font, stroke_width=2)
            x = ((im.width + 40) - text_width) / 2
            canvas.text(
                (x, y),
                page,
                font=font,
                fill=(255, 255, 255),
                align="center",
                spacing=2,
                stroke_width=2,
                stroke_fill=(0, 0, 0),
            )
            y += 25

        fp = BytesIO()
        im.save(fp, "PNG")
        fp.seek(0)
        im.close()
        _file = discord.File(fp, "horny.png")
        fp.close()
        return _file

    def gen_horny(self, member_avatar):
        member_avatar = self.bytes_to_image(member_avatar, 85)
        # base canvas
        im = Image.new("RGBA", (360, 300), None)
        card = Image.open(f"{bundled_data_path(self)}/horny/horny.png", mode="r").convert("RGBA")

        # pasting the pfp
        member_avatar = member_avatar.rotate(angle=22, resample=Image.BILINEAR, expand=True)
        im.paste(member_avatar, (43, 117))
        member_avatar.close()

        # pasting the card
        im.paste(card, (0, 0), card)
        card.close()

        fp = BytesIO()
        im.save(fp, "PNG")
        fp.seek(0)
        im.close()
        _file = discord.File(fp, "horny.png")
        fp.close()
        return _file

    def gen_shut(self, ctx, member_avatar, text: str, *, biden_avatar=None):
        member_avatar = self.bytes_to_image(member_avatar, 135)
        # base canvas
        im = Image.open(f"{bundled_data_path(self)}/shutup/shutup.png", mode="r").convert("RGBA")

        # avatars
        im.paste(member_avatar, (49, 2), member_avatar)
        member_avatar.close()
        if biden_avatar:
            biden_avatar = self.bytes_to_image(biden_avatar, 178)
            im.paste(biden_avatar, (372, 0), biden_avatar)

        # text
        font = ImageFont.truetype(f"{bundled_data_path(self)}/arial.ttf", 20)
        canvas = ImageDraw.Draw(im)
        pages = list(pagify(text, [" "], page_length=40))[:2]
        y = 250 - (len(pages) * 25)
        for page in pages:
            text_width, text_height = canvas.textsize(page, font, stroke_width=2)
            x = ((im.width - 300) - text_width) / 2
            canvas.text(
                (x, y),
                page,
                font=font,
                fill=(255, 255, 255),
                align="center",
                spacing=2,
                stroke_width=2,
                stroke_fill=(0, 0, 0),
            )
            y += 25

        fp = BytesIO()
        im.save(fp, "PNG")
        fp.seek(0)
        im.close()
        _file = discord.File(fp, "shutup.png")
        fp.close()
        return _file
