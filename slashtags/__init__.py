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
import re
from pathlib import Path

from redbot.core.bot import Red
from redbot.core.errors import CogLoadError

from .core import SlashTags
from .http import *  # noqa
from .objects import *  # noqa
from .testing.button_menus import *  # noqa
from .utils import validate_tagscriptengine

VERSION_RE = re.compile(r"TagScript==(\d\.\d\.\d)")

with open(Path(__file__).parent / "info.json") as fp:
    data = json.load(fp)

__red_end_user_data_statement__ = data["end_user_data_statement"]

tse_version = None
for requirement in data.get("requirements", []):
    match = VERSION_RE.search(requirement)
    if match:
        tse_version = match.group(1)
        break

if not tse_version:
    raise CogLoadError(
        "Failed to find TagScriptEngine version number. Please report this to the cog author."
    )


async def setup(bot: Red):
    await validate_tagscriptengine(bot, tse_version)
    cog = SlashTags(bot)
    await cog.pre_load()
    bot.add_cog(cog)
