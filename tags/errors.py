from typing import Optional


class MissingTagPermissions(Exception):
    """Raised when a user doesn't have permissions to use a block in a tag."""


class RequireCheckFailure(Exception):
    """
    Raised during tag invocation if the user fails to fulfill
    blacklist or whitelist requirements.
    """

    def __init__(self, response: Optional[str] = None):
        self.response = response
        super().__init__(response)


class WhitelistCheckFailure(RequireCheckFailure):
    """Raised when a user is not in a whitelisted channel or has a whitelisted role."""


class BlacklistCheckFailure(RequireCheckFailure):
    """Raised when a user is in a blacklisted channel or has a blacklisted role."""
