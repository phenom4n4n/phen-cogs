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

from typing import Optional

from redbot.core.commands import UserFeedbackCheckFailure
from redbot.core.utils.chat_formatting import humanize_number as hn

__all__ = (
    "TagError",
    "MissingTagPermissions",
    "RequireCheckFailure",
    "WhitelistCheckFailure",
    "BlacklistCheckFailure",
    "TagFeedbackError",
    "TagAliasError",
)


class TagError(Exception):
    """Base exception class."""


class MissingTagPermissions(TagError):
    """Raised when a user doesn't have permissions to use a block in a tag."""


class RequireCheckFailure(TagError):
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


class TagFeedbackError(UserFeedbackCheckFailure, TagError):
    """Provides feedback to the user when running tag commands."""


class TagAliasError(TagFeedbackError):
    """Raised to provide feedback if an error occurs while adding/removing a tag alias."""


class BlockCompileError(TagError):
    """Raised when a block fails to compile."""


class TagCharacterLimitReached(TagError):
    """Raised when the TagScript character limit is reached."""

    def __init__(self, limit: int, length: int):
        super().__init__(f"TagScript cannot be longer than {hn(limit)} (**{hn(length)}**).")
