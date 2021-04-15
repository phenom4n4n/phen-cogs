class WebhookError(RuntimeError):
    """Base class for Webhook cog exceptions."""


class InvalidWebhook(WebhookError):
    """Raised if given webhook link is invalid"""


class WebhookNotMatched(WebhookError):
    """Raised if given string isn't matched against webhook url."""
