from asyncio import create_task
import json
from pathlib import Path

from redbot.core.bot import Red

from .pfpimgen import PfpImgen

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]

# from https://github.com/phenom4n4n/Fixator10-Cogs/blob/V3/adminutils/__init__.py
async def setup_after_ready(bot):
    await bot.wait_until_red_ready()
    cog = PfpImgen(bot)
    for name, command in cog.all_commands.items():
        if not command.parent:
            if bot.get_command(name):
                command.name = f"i{command.name}"
            for alias in command.aliases:
                if bot.get_command(alias):
                    command.aliases[command.aliases.index(alias)] = f"i{alias}"
    bot.add_cog(cog)


def setup(bot):
    create_task(setup_after_ready(bot))
