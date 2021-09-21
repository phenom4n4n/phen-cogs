from __future__ import annotations

from typing import TYPE_CHECKING, Tuple, Optional

import discord

from .core import Connect4Game

if TYPE_CHECKING:
    from .connect4 import Connect4
    from redbot.core import commands


class BaseView(discord.ui.View):
    def __init__(self, *args, user_id: Optional[int] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.message: discord.Message = None
        self.user_id: Optional[int] = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You haven't been challenged.", ephemeral=True)
            return False
        return True

    def disable_items(self, *, ignore_color: Tuple[discord.ui.Button] = ()):
        for item in self.children:
            if hasattr(item, "style") and item not in ignore_color:
                item.style = discord.ButtonStyle.gray
            item.disabled = True


class ConfirmationView(BaseView):
    def __init__(self, ctx: commands.Context, timeout: int = 60, *, user_id: int = None):
        super().__init__(timeout=timeout, user_id=user_id)
        self.ctx = ctx
        self.value = None

    async def send_initial_message(
        self, ctx: commands.Context, content: str = None, **kwargs
    ) -> discord.Message:
        if not self.user_id:
            self.user_id = ctx.author.id
        message = await ctx.reply(content, view=self, **kwargs)
        self.message = message
        return message

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = True
        self.stop()
        await interaction.message.delete()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = False
        self.stop()
        await interaction.followup.send("Game offer declined, cancelling.")
        await interaction.message.delete()

    async def on_timeout(self):
        self.disable_items()
        await self.message.edit(view=self)

    @classmethod
    async def confirm(
        cls, ctx: commands.Context, content: str = None, timeout: int = 60, *, user_id: int, **kwargs
    ) -> bool:
        view = cls(ctx, timeout=timeout, user_id=user_id)
        await view.send_initial_message(ctx, content, **kwargs)
        await view.wait()
        return view.value


class Connect4Button(discord.ui.Button["Connect4View"]):
    @property
    def game(self) -> Connect4Game:
        return self.view.game


class DigitButton(Connect4Button):
    def __init__(self, digit: int):
        self.digit = digit
        super().__init__(style=discord.ButtonStyle.red, emoji=f"{digit}\N{combining enclosing keycap}")

    async def callback(self, interaction: discord.Interaction):
        self.game.move(self.digit - 1)
        if self.game.whomst_won() != self.game.NO_WINNER:
            await self.view.end(interaction, win=True)
        else:
            self.view.recolor()
            await interaction.response.edit_message(content=self.game, view=self.view)


class CancelButton(Connect4Button):
    def __init__(self, emoji: str):
        super().__init__(style=discord.ButtonStyle.gray, emoji=emoji)

    async def callback(self, interaction: discord.Interaction):
        self.game.forfeit()
        await self.view.end(interaction)


class Connect4View(discord.ui.View):
    CANCEL_EMOJI = "🚫"
    DIGITS = range(1, 8)
    TIMEOUT = 2 * 60

    def __init__(self, cog: Connect4, game: Connect4Game):
        self.cog = cog
        self.game = game
        super().__init__(
            timeout=self.TIMEOUT,
        )
        for digit in self.DIGITS:
            self.add_item(DigitButton(digit))
        self.cancel_button = CancelButton(self.CANCEL_EMOJI)
        self.add_item(self.cancel_button)
        self.ctx: Optional[commands.Context] = None

    async def interaction_check(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if user_id not in self.game.player_ids:
            await interaction.response.send_message("You aren't playing this Connect 4 game!", ephemeral=True)
            return False
        if user_id != self.game.current_player.id:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        self.game.forfeit()
        self.disable_items()
        await self.message.edit(view=self)
        await self.ctx.send("Connect4 game timed out.")

    async def start(self, ctx: commands.Context) -> discord.Message:
        self.ctx = ctx
        message = await ctx.send(self.game, view=self)
        self.message = message
        return message

    async def end(self, interaction: discord.Interaction, *, win: bool = False):
        self.stop()
        if not win:
            self.disable_items(ignore_color=(self.cancel_button,))
        await interaction.response.edit_message(content=self.game, view=None if win else self)

    def disable_items(self, *, ignore_color: Tuple[discord.ui.Button] = ()):
        for item in self.children:
            if hasattr(item, "style") and item not in ignore_color:
                item.style = discord.ButtonStyle.gray
            item.disabled = True

    def recolor(self):
        style = discord.ButtonStyle.red if self.game.whomst_turn() == 1 else discord.ButtonStyle.blurple
        for button in self.children:
            if isinstance(button, CancelButton):
                continue
            button.style = style
