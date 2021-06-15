"""
MIT License

Copyright (c) 2020-2021 phenom4n4n

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

import json
from pathlib import Path

from redbot.core.bot import Red
from redbot.core.errors import CogLoadError

from .core import Tags

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


conflicting_cogs = (
    ("Alias", "alias", "aliases"),
    ("CustomCommands", "customcom", "custom commands"),
)


def setup(bot: Red) -> None:
    for cog_name, module_name, tag_name in conflicting_cogs:
        if bot.get_cog(cog_name):
            raise CogLoadError(
                f"This cog conflicts with {cog_name} and both cannot be loaded at the same time. "
                f"After unloading `{module_name}`, you can migrate {tag_name} to tags with `[p]migrate{module_name}`."
            )
    bot.add_cog(Tags(bot))
