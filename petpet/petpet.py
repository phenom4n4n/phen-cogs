import asyncio
import functools
from io import BytesIO
from typing import Literal

import discord
from PIL import Image
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.data_manager import bundled_data_path

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class PetPet(commands.Cog):
    """
    Make petpet gifs!
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=23457892378904578923089489,
            force_registration=True,
        )

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        return

    @commands.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(cooldown_after_parsing=True)
    async def petpet(self, ctx, *, member: discord.Member = None):
        """PetPet someone."""
        member = member or ctx.author
        async with ctx.typing():
            avatar = await self.get_avatar(member)
            task = functools.partial(self.gen_petpet, ctx, avatar)
            image = await self.generate_image(ctx, task)
        if isinstance(image, str):
            await ctx.send(image)
        else:
            for im in image:
                await ctx.send(file=im)

    async def get_avatar(self, member: discord.User):
        avatar = BytesIO()
        await member.avatar_url.save(avatar, seek_begin=True)
        return avatar

    def bytes_to_image(self, avatar: BytesIO, size: int):
        image = Image.open(avatar).convert("RGBA")
        image = image.resize((size, size), Image.ANTIALIAS)
        avatar.close()
        return image

    async def generate_image(self, ctx: commands.Context, task: functools.partial):
        task = self.bot.loop.run_in_executor(None, task)
        try:
            image = await asyncio.wait_for(task, timeout=60)
        except asyncio.TimeoutError:
            return "An error occurred while generating this image. Try again later."
        else:
            return image

    def gen_petpet(self, ctx: commands.Context, member_avatar: BytesIO):
        member_avatar = self.bytes_to_image(member_avatar, 75)
        # base canvas
        sprite = Image.open(f"{bundled_data_path(self)}/sprite.png", mode="r").convert("RGBA")

        # pasting the pfp
        images = []
        for index in range(5):
            im = Image.new("RGBA", (100, 100), None)
            im.paste(member_avatar, (25, 25), member_avatar)
            im.paste(sprite, (0 - (112 * index), 0), sprite)
            images.append(im)
        sprite.close()
        member_avatar.close()

        fp = BytesIO()
        images[0].save(
            fp,
            "GIF",
            save_all=True,
            append_images=images[1:],
            loop=0,
            disposal=2,
        )
        fp.seek(0)
        for im in images:
            im.close()
        _file = discord.File(fp, "petpet.gif")
        fp.close()
        return [_file]


"""
        files = []
        for im in images:
            fp = BytesIO()
            im.save(fp, "PNG")
            fp.seek(0)
            files.append(fp)
            fp.close()
        fp = BytesIO()
        imageio.mimsave(fp, images, "gif")
        fp.seek(0)
        _file = discord.File(fp, "petpet.gif")
        fp.close()
        return [_file]

        files = []
        for im in images:
            fp = BytesIO()
            im.save(fp, "PNG")
            fp.seek(0)
            _file = discord.File(fp, "petpet.png")
            fp.close()
            files.append(_file)
        return files

        fp = BytesIO()
        images[0].save(
            fp,
            "GIF",
            save_all=True,
            append_images=images[1:],
            loop=0,
            disposal=2,
        )
        fp.seek(0)
        for im in images:
            im.close()
        _file = discord.File(fp, "petpet.gif")
        fp.close()
        return _file
"""
