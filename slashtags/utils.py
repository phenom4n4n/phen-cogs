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

import re
from importlib import reload

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.errors import CogLoadError

VALID_NAME = r"[\w-]{1,32}"

SLASH_NAME = re.compile(r"^{?(%s)}?$" % VALID_NAME)

ARGUMENT_NAME_DESCRIPTION = re.compile(r"^(%s):(.{1,100})$" % VALID_NAME)


def dev_check(ctx: commands.Context):
    return ctx.bot.get_cog("Dev")


async def validate_tagscriptengine(bot: Red, tse_version: str, *, reloaded: bool = False):
    try:
        import TagScriptEngine as tse
    except ImportError as exc:
        raise CogLoadError(
            "The SlashTags cog failed to install TagScriptEngine. Reinstall the cog and restart your "
            "bot. If it continues to fail to load, contact the cog author."
        ) from exc

    commands = [
        "`pip(3) uninstall -y TagScriptEngine`",
        "`pip(3) uninstall -y TagScript`",
        f"`pip(3) install TagScript=={tse_version}`",
    ]
    commands = "\n".join(commands)

    message = (
        "The SlashTags cog attempted to install TagScriptEngine, but the version installed "
        "is outdated. Shut down your bot, then in shell in your venv, run the following "
        f"commands:\n{commands}\nAfter running these commands, restart your bot and reinstall "
        "Tags. If it continues to fail to load, contact the cog author."
    )

    if not hasattr(tse, "VersionInfo"):
        if not reloaded:
            reload(tse)
            await validate_tagscriptengine(bot, tse_version, reloaded=True)
            return

        await bot.send_to_owners(message)
        raise CogLoadError(message)

    if tse.version_info < tse.VersionInfo.from_str(tse_version):
        await bot.send_to_owners(message)
        raise CogLoadError(message)


def chunks(l, n):
    """
    Yield successive n-sized chunks from l.
    https://github.com/flaree/flare-cogs/blob/08b78e33ab814aa4da5422d81a5037ae3df51d4e/commandstats/commandstats.py#L16
    """
    for i in range(0, len(l), n):
        yield l[i : i + n]
