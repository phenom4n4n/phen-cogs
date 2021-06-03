import logging
from collections import namedtuple

import akinator
import discord
from akinator.async_aki import Akinator
from redbot.core import commands
from redbot.vendored.discord.ext import menus

log = logging.getLogger("red.phenom4n4n.aki.menus")

NSFW_WORDS = ["porn", "sex"]

YES = "✅"
NO = "❌"
IDK = "❔"
PROBABLY = "📉"
PROBABLY_NOT = "📈"
BACK = "🔙"
WIN = "🏆"
CANCEL = "🗑️"

button_meta = namedtuple("ButtonMeta", "style label")

EMOJI_BUTTONS = {
    YES: button_meta(style=3, label="yes"),
    NO: button_meta(style=4, label="no"),
    IDK: button_meta(style=1, label="idk"),
    PROBABLY: button_meta(style=1, label="probably"),
    PROBABLY_NOT: button_meta(style=1, label="probably not"),
    BACK: button_meta(style=2, label="back"),
    WIN: button_meta(style=2, label="win"),
    CANCEL: button_meta(style=2, label="cancel"),
}


def channel_is_nsfw(channel) -> bool:
    return getattr(channel, "nsfw", False)


class AkiMenu(menus.Menu):
    def __init__(self, game: Akinator, color: discord.Color):
        self.aki = game
        self.color = color
        self.num = 1
        self.message = None
        super().__init__(timeout=60, delete_message_after=False, clear_reactions_after=True)

    async def send_initial_message(self, ctx: commands.Context, channel: discord.TextChannel):
        return await channel.send(embed=self.current_question_embed())

    @menus.button(YES)
    async def yes(self, payload: discord.RawReactionActionEvent):
        self.num += 1
        await self.answer("yes", payload)
        await self.send_current_question(payload)

    @menus.button(NO)
    async def no(self, payload: discord.RawReactionActionEvent):
        self.num += 1
        await self.answer("no", payload)
        await self.send_current_question(payload)

    @menus.button(IDK)
    async def idk(self, payload: discord.RawReactionActionEvent):
        self.num += 1
        await self.answer("idk", payload)
        await self.send_current_question(payload)

    @menus.button(PROBABLY)
    async def probably(self, payload: discord.RawReactionActionEvent):
        self.num += 1
        await self.answer("probably", payload)
        await self.send_current_question(payload)

    @menus.button(PROBABLY_NOT)
    async def probably_not(self, payload: discord.RawReactionActionEvent):
        self.num += 1
        await self.answer("probably not", payload)
        await self.send_current_question(payload)

    @menus.button(BACK)
    async def back(self, payload: discord.RawReactionActionEvent):
        try:
            await self.aki.back()
        except akinator.CantGoBackAnyFurther:
            await self.send(
                payload,
                "You can't go back on the first question, try a different option instead.",
                delete_after=10,
            )
        else:
            self.num -= 1
            await self.send_current_question(payload)

    async def send(self, payload, content: str = None, **kwargs):
        await self.ctx.send(content, **kwargs)

    @menus.button(WIN)
    async def react_win(self, payload: discord.RawReactionActionEvent):
        await self.win(payload)

    @menus.button(CANCEL)
    async def end(self, payload: discord.RawReactionActionEvent):
        await self.message.delete()
        self.stop()

    def current_question_embed(self):
        e = discord.Embed(
            color=self.color,
            title=f"Question #{self.num}",
            description=self.aki.question,
        )
        if self.aki.progression > 0:
            e.set_footer(text=f"{round(self.aki.progression, 2)}% guessed")
        return e

    def get_winner_embed(self, winner: dict) -> discord.Embed:
        win_embed = discord.Embed(
            color=self.color,
            title=f"I'm {round(float(winner['proba']) * 100)}% sure it's {winner['name']}!",
            description=winner["description"],
        )
        win_embed.set_image(url=winner["absolute_picture_path"])
        return win_embed

    def get_nsfw_embed(self):
        return discord.Embed(
            color=self.color,
            title="I guessed it, but this result is inappropriate.",
            description="Try again in a NSFW channel.",
        )

    def text_is_nsfw(self, text: str) -> bool:
        text = text.lower()
        return any(word in text for word in NSFW_WORDS)

    async def win(self, payload):
        winner = await self.aki.win()
        description = winner["description"]
        if not channel_is_nsfw(self.message.channel) and self.text_is_nsfw(description):
            embed = self.get_nsfw_embed()
        else:
            embed = self.get_winner_embed(winner)
        await self.edit_or_send(payload, embed=embed, components=[])
        self.stop()
        # TODO allow for continuation of game

    async def edit(self, payload, **kwargs):
        await self.message.edit(embed=self.current_question_embed())

    async def send_current_question(self, payload):
        if self.aki.progression < 80:
            try:
                await self.edit(payload, embed=self.current_question_embed())
            except discord.HTTPException:
                await self.cancel(payload)
        else:
            await self.win(payload)

    async def finalize(self, timed_out: bool):
        if timed_out:
            await self.edit_or_send(
                None, content="Akinator game timed out.", embed=None, components=[]
            )

    async def cancel(self, payload, message: str = "Akinator game cancelled."):
        await self.edit_or_send(payload, content=message, embed=None, components=[])
        self.stop()

    async def edit_or_send(self, payload, **kwargs):
        try:
            await self.message.edit(**kwargs)
        except discord.NotFound:
            await self.ctx.send(**kwargs)
        except discord.Forbidden:
            pass

    async def answer(self, message: str, payload):
        try:
            await self.aki.answer(message)
        except akinator.AkiNoQuestions:
            await self.win(payload)
        except akinator.AkiTimedOut:
            await self.cancel("The connection to the Akinator servers was lost.")
        except Exception as error:
            log.exception(
                f"Encountered an exception while answering with {message} during Akinator session",
                exc_info=True,
            )
            await self.edit_or_send(
                payload, content=f"Akinator game errored out:\n`{error}`", embed=None
            )
            self.stop()


def get_menu(*, buttons: bool):
    if not buttons:
        return AkiMenu
    try:
        from slashtags import Button, ButtonMenuMixin, ButtonStyle
    except ImportError:
        return AkiMenu

    class AkiButtonMixin(ButtonMenuMixin):
        def _get_component_from_emoji(self, emoji: discord.PartialEmoji) -> Button:
            meta = EMOJI_BUTTONS[str(emoji)]
            return Button(
                style=ButtonStyle(meta.style),
                custom_id=f"{self.custom_id}-{emoji}",
                label=meta.label,
                # emoji=emoji,
            )

    class AkiButtonMenu(AkiButtonMixin, AkiMenu):
        async def update(self, button):
            await button.defer_update()
            await super().update(button)

        async def send_initial_message(self, ctx: commands.Context, channel: discord.TextChannel):
            self.custom_id = str(ctx.message.id)
            return await self._send(ctx, embed=self.current_question_embed())

        async def edit(self, button, **kwargs):
            await button.update(embed=self.current_question_embed())

        async def send(self, button, content: str = None, **kwargs):
            await button.send(content, **kwargs)

        async def edit_or_send(self, button, **kwargs):
            try:
                if button:
                    await button.update(**kwargs)
                else:
                    if kwargs.pop("components", None) == []:
                        await self._edit_message_components([])
                    await self.message.edit(**kwargs)
            except discord.NotFound:
                await self.ctx.send(**kwargs)
            except discord.Forbidden:
                pass

    return AkiButtonMenu
