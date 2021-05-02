from discord import AsyncWebhookAdapter, Webhook
from redbot.core.commands import BadArgument, Context, Converter

from .errors import WebhookNotMatched
from .utils import WEBHOOK_RE


class WebhookLinkConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> Webhook:
        cog = ctx.bot.get_cog("Webhook")
        await cog.delete_quietly(ctx)
        try:
            return cog.get_webhook_from_link(argument)
        except WebhookNotMatched as e:
            raise BadArgument(str(e)) from e
