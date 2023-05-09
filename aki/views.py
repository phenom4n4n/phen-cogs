import logging

import akinator
import discord
from akinator.async_aki import Akinator
from redbot.core import commands

log = logging.getLogger("red.phenom4n4n.aki.menus")

NSFW_WORDS = ("porn", "sex")


def channel_is_nsfw(channel) -> bool:
    return getattr(channel, "nsfw", False)


class AkiView(discord.ui.View):
    def __init__(self, game: Akinator, color: discord.Color, *, author_id: int):
        self.aki = game
        self.color = color
        self.num = 1
        self.author_id = author_id
        super().__init__(timeout=60)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This isn't your Akinator game.", ephemeral=True
            )
            return False
        await interaction.response.defer()
        return True

    async def send_initial_message(
        self, ctx: commands.Context, channel: discord.TextChannel
    ) -> discord.Message:
        return await channel.send(embed=self.current_question_embed(), view=self)

    async def start(self, ctx: commands.Context) -> discord.Message:
        return await self.send_initial_message(ctx, ctx.channel)

    @discord.ui.button(label="yes", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.answer_question("yes", interaction)

    @discord.ui.button(label="no", style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.answer_question("no", interaction)

    @discord.ui.button(label="idk", style=discord.ButtonStyle.blurple)
    async def idk(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.answer_question("idk", interaction)

    @discord.ui.button(label="probably", style=discord.ButtonStyle.blurple)
    async def probably(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.answer_question("probably", interaction)

    @discord.ui.button(label="probably not", style=discord.ButtonStyle.blurple)
    async def probably_not(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.answer_question("probably not", interaction)

    @discord.ui.button(label="back", style=discord.ButtonStyle.gray)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.aki.back()
        except akinator.CantGoBackAnyFurther:
            await interaction.followup.send(
                "You can't go back on the first question, try a different option instead.",
                ephemeral=True,
            )
        else:
            self.num -= 1
            await self.send_current_question(interaction)

    @discord.ui.button(label="win", style=discord.ButtonStyle.gray)
    async def react_win(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.win(interaction)

    @discord.ui.button(label="cancel", style=discord.ButtonStyle.gray)
    async def end(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        self.stop()

    async def answer_question(self, answer: str, interaction: discord.Interaction):
        self.num += 1
        await self.answer(answer, interaction)
        await self.send_current_question(interaction)

    async def answer(self, message: str, interaction: discord.Interaction):
        try:
            await self.aki.answer(message)
        except akinator.AkiNoQuestions:
            await self.win(interaction)
        except akinator.AkiTimedOut:
            await self.cancel(interaction, "The connection to the Akinator servers was lost.")
        except Exception as error:
            log.exception(
                f"Encountered an exception while answering with {message} during Akinator session",
                exc_info=True,
            )
            await self.edit_or_send(
                interaction, content=f"Akinator game errored out:\n`{error}`", embed=None
            )
            self.stop()

    async def edit_or_send(self, interaction: discord.Interaction, **kwargs):
        try:
            await interaction.message.edit(**kwargs)
        except discord.NotFound:
            await interaction.followup.send(**kwargs)
        except discord.Forbidden:
            pass

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

    async def win(self, interaction: discord.Interaction):
        try:
            winner = await self.aki.win()
            description = winner["description"]
            if not channel_is_nsfw(self.message.channel) and self.text_is_nsfw(description):
                embed = self.get_nsfw_embed()
            else:
                embed = self.get_winner_embed(winner)
        except Exception as e:
            log.exception("An error occurred while trying to win an Akinator game.", exc_info=e)
            embed = discord.Embed(
                color=self.color,
                title="An error occurred while trying to win the game.",
                description="Try again later.",
            )
        await interaction.message.edit(embed=embed, view=None)
        self.stop()
        # TODO allow for continuation of game

    async def edit(self, interaction: discord.Interaction):
        await interaction.message.edit(embed=self.current_question_embed(), view=self)

    async def cancel(
        self, interaction: discord.Interaction, message: str = "Akinator game cancelled."
    ):
        await self.edit_or_send(interaction, content=message, embed=None, view=None)
        self.stop()

    async def send_current_question(self, interaction: discord.Interaction):
        if self.aki.progression < 80:
            try:
                await self.edit(interaction)
            except discord.HTTPException:
                await self.cancel(interaction)
        else:
            await self.win(interaction)
