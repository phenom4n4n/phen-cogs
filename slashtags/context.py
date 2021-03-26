from discord import Message
from redbot.core import commands

from .models import InteractionResponse


class SlashContext(commands.Context):
    def __init__(self, *, message: InteractionResponse, **kwargs):
        self.interaction: InteractionResponse = message
        super().__init__(message=message, **kwargs)
        self.send = message.send

    def __repr__(self):
        return (
            "<SlashContext interaction={0.interaction!r} invoked_with={0.invoked_with!r}>".format(
                self
            )
        )

    @classmethod
    def from_interaction(cls, interaction: InteractionResponse):
        args_values = [o.value for o in interaction.options]
        return cls(
            message=interaction,
            bot=interaction.bot,
            args=args_values,
            prefix="/",
            command=interaction.command,
            invoked_with=interaction.command_name,
        )

    async def tick(self):
        await self.interaction.send("✅", hidden=True)
