from redbot.core.utils.menus import menu


def get_menu():
    try:
        from slashtags import menu as _menu
    except ImportError:
        _menu = menu
    return _menu
