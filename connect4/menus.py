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

import discord
from redbot.core import commands
from redbot.vendored.discord.ext import menus

from .core import Connect4Game


class Connect4Menu(menus.Menu):
    CANCEL_GAME_EMOJI = "🚫"
    DIGITS = [str(digit) + "\N{combining enclosing keycap}" for digit in range(1, 8)]
    GAME_TIMEOUT_THRESHOLD = 2 * 60

    def __init__(self, cog, game: Connect4Game):
        self.cog = cog
        self.game = game
        super().__init__(
            timeout=self.GAME_TIMEOUT_THRESHOLD,
            delete_message_after=False,
            clear_reactions_after=True,
        )
        for index, digit in enumerate(self.DIGITS):
            self.add_button(
                menus.Button(digit, self.handle_digit_press, position=menus.First(index))
            )

    def reaction_check(self, payload: discord.RawReactionActionEvent):
        if payload.message_id != self.message.id:
            return False
        if payload.user_id != self.game.current_player.id:
            return False
        return payload.emoji in self.buttons

    async def send_initial_message(
        self, ctx: commands.Context, channel: discord.TextChannel
    ) -> discord.Message:
        return await channel.send(self.game)

    def get_emoji_from_payload(self, payload: discord.RawReactionActionEvent) -> str:
        return str(payload.emoji)

    async def handle_digit_press(self, payload: discord.RawReactionActionEvent):
        try:
            # convert the reaction to a 0-indexed int and move in that column
            self.game.move(self.DIGITS.index(self.get_emoji_from_payload(payload)))
        except ValueError:
            pass  # the column may be full
        await self.edit(payload, content=self.game, refresh_components=True)
        if self.game.whomst_won() != self.game.NO_WINNER:
            await self.end()

    @menus.button(CANCEL_GAME_EMOJI, position=menus.Last(0))
    async def close_menu(self, payload: discord.RawReactionActionEvent):
        self.game.forfeit()
        await self.end()

    async def end(self):
        self.stop()

    async def edit(
        self, payload: discord.RawReactionActionEvent, *, respond: bool = True, **kwargs
    ):
        refresh_components = kwargs.pop("refresh_components", False)
        try:
            await self.message.edit(**kwargs)
        except discord.NotFound:
            await self.cancel(
                "Connect4 game cancelled since the message was deleted." if respond else None
            )
        except discord.Forbidden:
            await self.cancel(None)

    async def cancel(self, message: str = "Connect4 game cancelled."):
        if message:
            await self.ctx.send(message)
        self.stop()

    async def finalize(self, timed_out: bool):
        if timed_out:
            await self.ctx.send(content="Connect4 game timed out.")
        gameboard = str(self.game)
        if self.message.content != gameboard:
            await self.edit(None, content=gameboard, respond=False, components=[])
        await self.store_stats()

    @staticmethod
    def add_stat(stats: dict, key: str, user_id: str):
        if user_id in stats[key]:
            stats[key][user_id] += 1
        else:
            stats[key][user_id] = 1

    async def store_stats(self):
        winnernum = self.game.whomst_won()
        if winnernum in (Connect4Game.FORFEIT, Connect4Game.NO_WINNER):
            return

        player1_id = str(self.game.player1.id)
        player2_id = str(self.game.player2.id)
        async with self.cog.config.guild(self.message.guild).stats() as stats:
            stats["played"] += 1
            if winnernum == Connect4Game.TIE:
                stats["ties"] += 1
                self.add_stat(stats, "draw", player1_id)
                self.add_stat(stats, "draw", player2_id)
            else:
                winner, loser = (
                    (player1_id, player2_id) if winnernum == 1 else (player2_id, player1_id)
                )
                self.add_stat(stats, "wins", winner)
                self.add_stat(stats, "losses", loser)


def get_menu():
    try:
        from slashtags import Button, ButtonMenuMixin, ButtonStyle
    except ImportError:
        return Connect4Menu

    class Connect4ButtonMenu(ButtonMenuMixin, Connect4Menu):
        async def update(self, button):
            await button.defer_update()
            await super().update(button)

        def _get_component_from_emoji(self, emoji: discord.PartialEmoji) -> Button:
            if str(emoji) == self.CANCEL_GAME_EMOJI:
                style = ButtonStyle.grey
            else:
                style = ButtonStyle.red if self.game.whomst_turn() == 1 else ButtonStyle.blurple
            return Button(style=style, custom_id=f"{self.custom_id}-{emoji}", emoji=emoji)

        def get_emoji_from_payload(self, button):
            return str(self._get_emoji(button))

        async def send_initial_message(self, ctx: commands.Context, channel: discord.TextChannel):
            self.custom_id = str(ctx.message.id)
            return await self._send(ctx, self.game)

        async def edit(self, button, *, respond: bool = True, **kwargs):
            refresh_components = kwargs.pop("refresh_components", False)
            if refresh_components:
                kwargs["components"] = self._get_components()

            try:
                if button:
                    try:
                        await button.update(**kwargs)
                    except discord.NotFound:
                        await self.message_edit(button, respond=respond, **kwargs)
                else:
                    await self.message_edit(button, respond=respond, **kwargs)
            except discord.Forbidden:
                await self.cancel(None)

        async def message_edit(self, button, *, respond: bool = True, **kwargs):
            try:
                if kwargs.pop("components", None) == []:
                    await self._edit_message_components([], **kwargs)
                else:
                    await self.message.edit(**kwargs)
            except discord.NotFound:
                await self.cancel(
                    "Connect4 game cancelled since the message was deleted." if respond else None
                )

        def reaction_check(self, button):
            raw_message = button._original_data["message"]
            if int(raw_message["id"]) != self.message.id:
                return False
            if button.author_id not in self.game.player_ids:
                asyncio.create_task(
                    button.send("You aren't playing this Connect 4 game!", hidden=True)
                )
                return False
            if button.author_id != self.game.current_player.id:
                asyncio.create_task(button.send("It's not your turn!", hidden=True))
                return False
            return button.custom_id.startswith(self.custom_id)

    return Connect4ButtonMenu
