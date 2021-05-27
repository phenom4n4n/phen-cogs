import logging
from typing import Optional

import discord
from redbot.core import commands
from redbot.core.bot import Red

from ..http import Button, Component
from .button_menus import menu

log = logging.getLogger("red.phenom4n4n.slashtags.testing.test_cog")


class SlashTagTesting(commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.button_cache = {}

    @commands.is_owner()
    @commands.command()
    async def buttontest(
        self,
        ctx: commands.Context,
        style: Optional[int] = 1,
        emoji: Optional[discord.PartialEmoji] = None,
        label: str = "Button!",
    ):
        """Test buttons."""
        r = discord.http.Route(
            "POST", "/channels/{channel_id}/messages", channel_id=ctx.channel.id
        )
        data = {"content": "Here's your button."}
        button = Button(style=style, label=label, custom_id=ctx.message.id, emoji=emoji)
        self.button_cache[button.custom_id] = button
        components = Component(components=[button])
        data["components"] = [components.to_dict()]
        await self.bot._connection.http.request(r, json=data)

    @commands.is_owner()
    @commands.command()
    async def buttonmenu(self, ctx: commands.Context, *pages: str):
        """Create a menu with buttons."""
        await menu(ctx, ["page 1", "page 2", "page 3", *pages])
