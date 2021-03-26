import json
from pathlib import Path

from redbot.core.bot import Red

from .http import Route
from .models import SlashOptionType
from .slashtags import SlashTags

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red) -> None:
    cog = SlashTags(bot)
    await cog.pre_load()
    bot.add_cog(cog)
