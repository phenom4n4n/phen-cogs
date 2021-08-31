from importlib import reload

from redbot.core.bot import Red
from redbot.core.errors import CogLoadError
from redbot.core.utils.menus import menu


def get_menu():
    try:
        from slashtags import menu as _menu
    except ImportError:
        _menu = menu
    return _menu


async def validate_tagscriptengine(bot: Red, tse_version: str, *, reloaded: bool = False):
    try:
        import TagScriptEngine as tse
    except ImportError as exc:
        raise CogLoadError(
            "The Tags cog failed to install TagScriptEngine. Reinstall the cog and restart your "
            "bot. If it continues to fail to load, contact the cog author."
        ) from exc

    commands = [
        "`pip(3) uninstall -y TagScriptEngine`",
        "`pip(3) uninstall -y TagScript`",
        f"`pip(3) install TagScript=={tse_version}`",
    ]
    commands = "\n".join(commands)

    message = (
        "The Tags cog attempted to install TagScriptEngine, but the version installed "
        "is outdated. Shut down your bot, then in shell in your venv, run the following "
        f"commands:\n{commands}\nAfter running these commands, restart your bot and reload "
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
