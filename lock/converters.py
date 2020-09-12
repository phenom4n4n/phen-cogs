from redbot.core.commands import BadArgument

def channel_toggle(arg: str):
    arg = arg.lower()
    if arg not in ["true", "default", "nuetral"]:
        raise BadArgument(f"`{arg} is not a valid channel state. You use provide `true` or `default`.")
    if arg == "neutral" or arg == "default":
        arg = None
    elif arg == "true":
        arg = True
    return arg