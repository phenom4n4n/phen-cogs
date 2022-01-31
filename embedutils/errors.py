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

from redbot.core import commands

__all__ = (
    "EmbedUtilsException",
    "EmbedNotFound",
    "EmbedFileError",
    "EmbedLimitReached",
    "EmbedConversionError",
)


class EmbedUtilsException(Exception):
    """Base class for EmbedUtils exceptions."""


class EmbedNotFound(EmbedUtilsException):
    """Raised when an embed isn't found on a message."""


class EmbedFileError(EmbedUtilsException):
    """Provides error messages when users supply invalid/no embed files."""


class EmbedLimitReached(EmbedUtilsException):
    """Raised when the limit for embeds that can be stored has been reached."""


class EmbedConversionError(EmbedUtilsException):
    def __init__(self, ctx: commands.Context, error_type: str, error: Exception):
        self.ctx = ctx
        self.error_type = error_type
        self.error = error
        super().__init__(error)
