import re

import discord
from redbot.core.commands import Context

USER_MENTIONS = discord.AllowedMentions.none()
USER_MENTIONS.users = True

WEBHOOK_RE = re.compile(r"discord(?:app)?.com/api/webhooks/(?P<id>[0-9]{17,21})/(?P<token>[A-Za-z0-9\.\-\_]{60,68})")

async def _monkeypatch_send(
    ctx: Context, content: str = None, **kwargs
) -> discord.Message:
    self = ctx.bot.get_cog("Webhook")
    original_kwargs = kwargs.copy()
    try:
        webhook = await self.get_webhook(ctx=ctx)
        kwargs["username"] = ctx.author.display_name
        kwargs["avatar_url"] = ctx.author.avatar_url
        kwargs["wait"] = True
        return await webhook.send(content, **kwargs)
    except Exception:
        return await super(Context, ctx).send(content, **original_kwargs)

class FakeResponse:
    def __init__(self):
        self.status = 403
        self.reason = "Forbidden"
