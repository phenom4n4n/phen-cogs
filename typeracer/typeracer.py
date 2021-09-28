import asyncio
import textwrap
from difflib import SequenceMatcher
from functools import partial
from io import BytesIO
from typing import Optional, Tuple

import aiohttp
import discord
from PIL import Image, ImageDraw, ImageFont
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.data_manager import bundled_data_path
from redbot.core.utils.chat_formatting import humanize_number as hn


class TypeRacer(commands.Cog):
    """
    Race to see who can type the fastest!

    Credits to Cats3153.
    """

    FONT_SIZE = 30

    __version__ = "1.1.0"

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=37278923457234,
            force_registration=True,
        )
        self.session = aiohttp.ClientSession()
        self._font = None

        # Thanks Gareth
        self.ordinal = lambda n: "%d%s" % (
            n,
            "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
        )

        self.default_global = {"leaderboard": []}

        self.config.register_global(**self.default_global)

    def cog_unload(self) -> None:
        asyncio.create_task(self.session.close())

    def format_help_for_context(self, ctx: commands.Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\nCog Version: {self.__version__}"

    async def red_delete_data_for_user(self, *, requester: str, user_id: int) -> None:
        async with self.config.leaderboard() as lb:
            for user in lb.copy():
                if user["user_id"] == user_id:
                    lb.remove(user)

    async def get_quote(self) -> Tuple[str, str]:
        async with self.session.get("https://api.quotable.io/random") as resp:
            resp = await resp.json()
            return resp["content"], resp["author"]

    @property
    def font(self) -> ImageFont:
        if self._font is None:
            self._font = ImageFont.truetype(
                f"{bundled_data_path(self)}/Menlo.ttf", self.FONT_SIZE, encoding="unic"
            )
        return self._font

    def generate_image(self, text: str, color: discord.Color) -> discord.File:
        margin = 40
        newline = self.FONT_SIZE // 5

        wrapped = textwrap.wrap(text, width=35)
        text = "\n".join(line.strip() for line in wrapped)

        img_width = self.font.getsize(max(wrapped, key=len))[0] + 2 * margin
        img_height = self.FONT_SIZE * len(wrapped) + (len(wrapped) - 1) * newline + 2 * margin

        with Image.new("RGBA", (img_width, img_height)) as im:
            draw = ImageDraw.Draw(im)
            draw.multiline_text(
                (margin, margin), text, spacing=newline, font=self.font, fill=color.to_rgb()
            )

            buffer = BytesIO()
            im.save(buffer, "PNG")
            buffer.seek(0)

        return buffer

    async def render_typerace(self, text: str, color: discord.Color) -> discord.File:
        func = partial(self.generate_image, text, color)
        task = self.bot.loop.run_in_executor(None, func)
        try:
            return await asyncio.wait_for(task, timeout=60)
        except asyncio.TimeoutError:
            raise commands.UserFeedbackCheckFailure(
                "An error occurred while generating this image. Try again later."
            )

    @commands.command(aliases=["tr"])
    @commands.cooldown(1, 10, commands.BucketType.guild)
    @commands.max_concurrency(1, commands.BucketType.channel)
    async def typerace(self, ctx: commands.Context) -> None:
        """
        Begin a typing race!

        Credits to Cats3153.
        """
        try:
            quote, author = await self.get_quote()
        except KeyError:
            raise commands.UserFeedbackCheckFailure(
                "Could not fetch quote. Please try again later."
            )

        color = discord.Color.random()
        img = await self.render_typerace(quote, color)
        embed = discord.Embed(color=color)
        embed.set_image(url="attachment://typerace.png")
        if author:
            embed.set_footer(text=f"~ {author}")

        msg = await ctx.send(file=discord.File(img, "typerace.png"), embed=embed)
        acc: Optional[float] = None

        def check(m: discord.Message) -> bool:
            if m.channel != ctx.channel or m.author.bot or not m.content:
                return False  # if satisfied, skip accuracy check and return
            content = " ".join(m.content.split())  # remove duplicate spaces
            accuracy = SequenceMatcher(None, quote, content).ratio()

            if accuracy >= 0.95:
                nonlocal acc
                acc = accuracy * 100
                return True
            return False

        ref = msg.to_reference(fail_if_not_exists=False)
        try:
            winner = await ctx.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            embed = discord.Embed(
                color=discord.Color.blurple(),
                description=f"No one typed the [sentence]({msg.jump_url}) in time.",
            )
            return await ctx.send(embed=embed, reference=ref)

        seconds = (winner.created_at - msg.created_at).total_seconds()
        winner_ref = winner.to_reference(fail_if_not_exists=False)
        wpm = (len(quote) / 5) / (seconds / 60) * (acc / 100)

        lb = await self.config.leaderboard()

        winnerdata = {"user_id": ctx.author.id, "wpm": wpm}

        position = None
        movedup = False
        previouspos = None

        for pos, data in enumerate(lb):
            if data["user_id"] == ctx.author.id:
                previouspos = pos
                if data["wpm"] < wpm:
                    lb.remove(data)
                    movedup = True

            if data["wpm"] < wpm:
                position = pos

        if position is None:
            position = len(lb)

        if previouspos is None:
            movedup = True

        if movedup and position != previouspos:
            lb.insert(position, winnerdata)

            movedup_desc = (
                f"You moved up the leaderboard to **{self.ordinal(position + 1)}** place!"
            )
        else:
            movedup_desc = f"Your still in {self.ordinal(previouspos + 1)}, keep on trying!"

        await self.config.leaderboard.set(lb)

        description = (
            f"{winner.author.mention} typed the [sentence]({msg.jump_url}) in `{seconds:.2f}s` "
            f"with **{acc:.2f}%** accuracy. (**{wpm:.1f} WPM**)\n{movedup_desc}"
        )
        embed = discord.Embed(color=winner.author.color, description=description)
        await ctx.send(embed=embed, reference=winner_ref)

    @commands.command(aliases=["trlb"])
    async def trleaderboard(self, ctx):
        """
        Show the typeracer's top 10 faster typers!
        """

        lb = await self.config.leaderboard()

        description = ""
        shown = 0

        for place, typer in enumerate(lb, start=1):
            if place == 11:
                break
            try:
                user = await self.bot.get_or_fetch_user(typer["user_id"])
                username = user.name
            except discord.NotFound:
                username = "Unknown"
            description += f"**{self.ordinal(place)}** {username} **{typer['wpm']:.1f} WPM**\n"
            shown += 1

        embed = discord.Embed(
            title="TypeRacer's Top 10 Fastest Typers",
            description=description,
            colour=await ctx.embed_colour(),
        )
        embed.set_footer(text=f"Top {shown} of {hn(len(lb))} shown.")
        await ctx.send(embed=embed)
