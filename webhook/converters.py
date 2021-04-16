from discord import Webhook, AsyncWebhookAdapter
from redbot.core.commands import Converter, Context, BadArgument

from .utils import WEBHOOK_RE
from .errors import WebhookNotMatched


class WebhookLinkConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> Webhook:
        cog = ctx.bot.get_cog("Webhook")
        await cog.delete_quietly(ctx)
        try:
            return cog.get_webhook_from_link(argument)
        except WebhookNotMatched as e:
            raise BadArgument(e) from e
