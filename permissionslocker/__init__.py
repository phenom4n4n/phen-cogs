import json
from pathlib import Path

from redbot.core.bot import Red

from .permissionslocker import PermissionsLocker, before_invoke_hook

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red) -> None:
    bot.add_cog(PermissionsLocker(bot))
    bot.before_invoke(before_invoke_hook)


def teardown(bot: Red):
    bot.remove_before_invoke_hook(before_invoke_hook)
