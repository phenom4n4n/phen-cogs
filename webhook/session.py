from typing import Optional

import discord
from redbot.core.commands import Context

from .errors import InvalidWebhook


class Session:
    def __init__(
        self,
        cog,
        *,
        channel: discord.TextChannel,
        webhook: discord.Webhook,
        author: discord.Member,
    ):
        self.cog = cog
        self.channel = channel
        self.webhook = webhook
        self.author = author

    async def initialize(self, ctx: Context):
        e = discord.Embed(
            color=0x49FC95,
            title="Webhook Session Initiated",
            description=f"Session Created by `{self.author}`.",
        )
        try:
            await self.cog.webhook_link_send(
                self.webhook,
                username="Webhook Session",
                avatar_url="https://imgur.com/BMeddyn.png",
                embed=e,
            )
        except InvalidWebhook:
            await self.channel_send(
                "Session initialization failed as provided webhook link was invalid."
            )
        else:
            self.cog.webhook_sessions[self.channel.id] = self
            await self.channel_send(
                "I will send all messages in this channel to the webhook until the session "
                f"is closed with `{ctx.clean_prefix}webhook session close` or there are 2 minutes of inactivity.",
                embed=e,
            )

    async def send(self, content: str = None, **kwargs) -> Optional[discord.Message]:
        try:
            return await self.cog.webhook_link_send(self.webhook, content, **kwargs)
        except InvalidWebhook:
            await self.close()

    async def channel_send(self, content: str = None, **kwargs) -> Optional[discord.Message]:
        if self.channel.permissions_for(self.channel.guild.me).send_messages:
            await self.channel.send(content, **kwargs)

    async def close(self, *, reason: str = "Webhook session closed."):
        await self.channel_send(reason)
        try:
            del self.cog.webhook_sessions[self.channel.id]
        except KeyError:
            pass
