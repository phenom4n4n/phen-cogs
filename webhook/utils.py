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

import re

import discord
from redbot.core.commands import Context

USER_MENTIONS = discord.AllowedMentions.none()
USER_MENTIONS.users = True

WEBHOOK_RE = re.compile(
    r"discord(?:app)?.com/api/webhooks/(?P<id>[0-9]{17,21})/(?P<token>[A-Za-z0-9\.\-\_]{60,68})"
)


async def _monkeypatch_send(ctx: Context, content: str = None, **kwargs) -> discord.Message:
    self = ctx.bot.get_cog("Webhook")
    original_kwargs = kwargs.copy()
    try:
        webhook = await self.get_webhook(ctx=ctx)
        kwargs["username"] = ctx.author.display_name
        kwargs["avatar_url"] = ctx.author.avatar.url
        kwargs["wait"] = True
        return await webhook.send(content, **kwargs)
    except Exception:
        return await super(Context, ctx).send(content, **original_kwargs)


class FakeResponse:
    def __init__(self):
        self.status = 403
        self.reason = "Forbidden"
