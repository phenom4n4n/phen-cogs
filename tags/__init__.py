import json
from pathlib import Path

from redbot.core.bot import Red
from redbot.core.errors import CogLoadError

from .tags import Tags

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


def setup(bot: Red) -> None:
    cog = bot.get_cog("CustomCommands")
    if cog:
        raise CogLoadError(
            "This cog conflicts with CustomCommands and cannot be loaded with both at the same time."
        )
    bot.add_cog(Tags(bot))
