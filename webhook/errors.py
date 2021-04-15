class WebhookError(RuntimeError):
    """Base class for Webhook cog exceptions."""


class InvalidWebhook(WebhookError):
    pass


class WebhookNotMatched(WebhookError):
    """Raised if given string isn't matched against webhook url."""
