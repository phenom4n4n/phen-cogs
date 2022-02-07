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
