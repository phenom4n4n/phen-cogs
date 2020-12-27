from redbot.core.commands import Context


class SilentContext(Context):
    async def send(self, content: str = None, **kwargs):
        pass
