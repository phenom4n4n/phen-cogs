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

DISC_DOC = "This must be in the format expected by [this Discord documentation](https://discord.com/developers/docs/resources/channel#embed-object)."


def _example(info_type: str, example_link: str) -> str:
    example = f"Here's [a {info_type} example]({example_link})."
    return f"{DISC_DOC}\n{example}"


INFO_EXAMPLES = {
    "json": _example(
        "json", "https://gist.github.com/TwinDragon/9cf12da39f6b2888c8d71865eb7eb6a8"
    ),
    "yaml": _example(
        "yaml", "https://gist.github.com/phenom4n4n/9ab118b8ec7911954499b150d0182c60"
    ),
    "index": "If the message has multiple embeds, you can pass a number to `index` to specify which embed.",
    "pastebin": _example("pastebin", "https://pastebin.com/YarwmY1v"),
}


def _add_example_help(pre_processed: str, *, info_type: str = "json") -> str:
    n = "\n" if "\n\n" not in pre_processed else ""
    info_type = info_type.lower()
    info = INFO_EXAMPLES[info_type]
    return f"{pre_processed}{n}\n{info}"


class HelpFormatter:
    def __init__(self, *args, **kwargs):
        add_example_info = kwargs.pop("add_example_info", False)
        info_type = kwargs.pop("info_type", "json")
        super().__init__(*args, **kwargs)
        self._add_example_info = add_example_info
        self._info_type = info_type

    def format_help_for_context(self, ctx: commands.Context):
        pre_processed = super().format_help_for_context(ctx)
        if self._add_example_info:
            return _add_example_help(pre_processed, info_type=self._info_type)
        return pre_processed


class HelpFormattedCommand(HelpFormatter, commands.Command):
    ...


class HelpFormattedGroup(HelpFormatter, commands.Group):
    def command(self, name=None, cls=HelpFormattedCommand, **kwargs):
        return super().command(name, cls, **kwargs)

    def group(self, name=None, cls=None, **kwargs):
        if cls is None:
            cls = type(self)
        return super().group(name, cls, **kwargs)


def help_formatted_command(name=None, cls=HelpFormattedCommand, **attrs):
    return commands.command(name, cls, **attrs)


def help_formatted_group(name=None, cls=HelpFormattedGroup, **attrs):
    return commands.group(name, cls, **attrs)
