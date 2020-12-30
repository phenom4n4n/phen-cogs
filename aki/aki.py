from typing import Literal

import akinator
import discord
from akinator.async_aki import Akinator
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.vendored.discord.ext import menus

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class AkiMenu(menus.Menu):
    def __init__(self, game: Akinator, color: discord.Color):
        self.aki = game
        self.color = color
        self.num = 1
        self.message = None
        super().__init__(timeout=60, delete_message_after=False, clear_reactions_after=True)

    async def send_initial_message(self, ctx: commands.Context, channel: discord.TextChannel):
        return await channel.send(embed=self.current_question_embed())

    @menus.button("✅")
    async def yes(self, payload: discord.RawReactionActionEvent):
        self.num += 1
        await self.aki.answer("yes")
        await self.send_current_question()

    @menus.button("❎")
    async def no(self, payload: discord.RawReactionActionEvent):
        self.num += 1
        await self.aki.answer("no")
        await self.send_current_question()

    @menus.button("❔")
    async def idk(self, payload: discord.RawReactionActionEvent):
        self.num += 1
        await self.aki.answer("idk")
        await self.send_current_question()

    @menus.button("📉")
    async def probably(self, payload: discord.RawReactionActionEvent):
        self.num += 1
        await self.aki.answer("probably")
        await self.send_current_question()

    @menus.button("📈")
    async def probably_not(self, payload: discord.RawReactionActionEvent):
        self.num += 1
        await self.aki.answer("probably not")
        await self.send_current_question()

    @menus.button("🔙")
    async def back(self, payload: discord.RawReactionActionEvent):
        try:
            await self.aki.back()
        except akinator.exceptions.CantGoBackAnyFurther:
            await self.ctx.send(
                "You can't go back on the first question, try a different option instead.",
                delete_after=10,
            )
        else:
            self.num -= 1
            await self.send_current_question()

    @menus.button("🏆")
    async def react_win(self, payload: discord.RawReactionActionEvent):
        await self.win()

    @menus.button("🗑️")
    async def end(self, payload: discord.RawReactionActionEvent):
        await self.cancel()

    def current_question_embed(self):
        e = discord.Embed(
            color=self.color,
            title=f"Question #{self.num}",
            description=self.aki.question,
        )
        if self.aki.progression > 0:
            e.set_footer(text=f"{round(self.aki.progression, 2)}% guessed")
        return e

    async def win(self):
        winner = await self.aki.win()
        win_embed = discord.Embed(
            color=self.color,
            title=f"I'm {round(float(winner['proba']) * 100)}% sure it's {winner['name']}!",
            description=winner["description"],
        )
        win_embed.set_image(url=winner["absolute_picture_path"])
        try:
            await self.message.edit(embed=win_embed)
        except discord.NotFound:
            await self.ctx.send(embed=win_embed)
        except discord.Forbidden:
            pass
        self.stop()
        # TODO allow for continuation of game

    async def send_current_question(self):
        if self.aki.progression < 80:
            try:
                await self.message.edit(embed=self.current_question_embed())
            except discord.HTTPException:
                await self.cancel()
        else:
            await self.win()

    async def finalize(self, timed_out: bool):
        if timed_out:
            try:
                await self.message.edit(content="Akinator game timed out.", embed=None)
            except discord.NotFound:
                await self.ctx.send("Akinator game timed out.")
            except discord.Forbidden:
                pass

    async def cancel(self):
        try:
            await self.message.edit(content="Akinator game cancelled.", embed=None)
        except discord.NotFound:
            await self.ctx.send("Akinator game cancelled.")
        except discord.Forbidden:
            pass
        self.stop()


class Aki(commands.Cog):
    """
    Play Akinator in Discord!
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=8237578807127857,
            force_registration=True,
        )
        self.emojis = {
            "✅": "yes",
            "❎": "no",
            "❔": "idk",
            "📉": "probably",
            "📈": "probably not",
            "🔙": "back",
            "🏆": "win",
            "🗑️": "end",
        }

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        return

    @commands.max_concurrency(1, commands.BucketType.channel)
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    @commands.group(invoke_without_command=True)
    async def aki(self, ctx: commands.Context):
        """
        Start a game of Akinator!

        Controls:
        > ✅ : yes
        > ❎ : no
        > ❔ : i don't know
        > 📉 : probably
        > 📈 : probably not
        > 🔙 : back
        > 🏆 : win
        > 🗑️ : cancel
        """
        await ctx.trigger_typing()
        aki = Akinator()
        try:
            await aki.start_game()
        except Exception:
            return await ctx.send(
                "I encountered an error while connecting to the Akinator servers."
            )
        menu = AkiMenu(aki, await ctx.embed_color())
        await menu.start(ctx)
