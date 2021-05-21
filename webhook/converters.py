from discord import Webhook
from redbot.core.commands import BadArgument, Context, Converter

from .errors import WebhookNotMatched


class WebhookLinkConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> Webhook:
        cog = ctx.bot.get_cog("Webhook")
        await cog.delete_quietly(ctx)
        try:
            return cog.get_webhook_from_link(argument)
        except WebhookNotMatched as e:
            raise BadArgument(str(e)) from e
