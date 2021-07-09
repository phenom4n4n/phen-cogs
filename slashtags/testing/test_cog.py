import logging
from typing import Optional

import discord
from redbot.core import commands
from redbot.core.bot import Red

from ..http import Button, ButtonStyle, Component, InteractionButton
from .button_menus import menu

log = logging.getLogger("red.phenom4n4n.slashtags.testing.test_cog")


class SlashTagTesting(commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.cookie_clickers = {}

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
        button = Button(
            style=ButtonStyle(style), label=label, custom_id=ctx.message.id, emoji=emoji
        )
        components = Component(components=[button])
        data["components"] = [components.to_dict()]
        await self.bot._connection.http.request(r, json=data)

    @commands.is_owner()
    @commands.command()
    async def buttonmenu(self, ctx: commands.Context, *pages: str):
        """Create a menu with buttons."""
        await menu(ctx, ["This is an example button menu.", *pages])

    @commands.command()
    async def cookieclicker(self, ctx: commands.Context):
        """Create a cookie clicker button menu."""
        r = discord.http.Route(
            "POST", "/channels/{channel_id}/messages", channel_id=ctx.channel.id
        )
        data = {"content": "Cookies clicked: 0."}
        button = Button(style=ButtonStyle.green, custom_id=str(ctx.message.id), emoji="🍪")
        components = Component(components=[button])
        self.cookie_clickers[button.custom_id] = 0
        data["components"] = [components.to_dict()]
        await self.bot._connection.http.request(r, json=data)

    @commands.Cog.listener()
    async def on_button_interaction(self, button: InteractionButton):
        try:
            clicks = self.cookie_clickers[button.custom_id]
        except KeyError:
            return
        await button.update(f"Cookies clicked: {clicks + 1}.")
        self.cookie_clickers[button.custom_id] += 1
