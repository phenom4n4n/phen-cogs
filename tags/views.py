from typing import Any, List, Optional, Tuple

import discord
from redbot.core import commands
from redbot.vendored.discord.ext.menus import ListPageSource

__all__ = ("ConfirmationView", "PageSource", "PaginatedView")


class BaseView(discord.ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message: discord.Message = None
        self._author_id: Optional[int] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self._author_id:
            await interaction.response.send_message("You can't do that.", ephemeral=True)
            return False
        return True

    def disable_items(self, *, ignore_color: Tuple[discord.ui.Button] = ()):
        for item in self.children:
            if hasattr(item, "style") and item not in ignore_color:
                item.style = discord.ButtonStyle.gray
            item.disabled = True


class ConfirmationView(BaseView):
    def __init__(self, timeout: int = 60, *, cancel_message: str = "Action cancelled."):
        super().__init__(timeout=timeout)
        self.value = None
        self.cancel_message = cancel_message

    async def send_initial_message(
        self, ctx: commands.Context, content: str = None, **kwargs
    ) -> discord.Message:
        self._author_id = ctx.author.id
        message = await ctx.reply(content, view=self, **kwargs)
        self.message = message
        return message

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        await self.disable_all(button, interaction)

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await self.disable_all(button, interaction)
        await interaction.followup.send(self.cancel_message, ephemeral=True)

    async def disable_all(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.disable_items(ignore_color=(button,))
        await interaction.response.edit_message(view=self)

    async def on_timeout(self):
        self.disable_items()
        await self.message.edit(view=self)

    @classmethod
    async def confirm(
        cls,
        ctx: commands.Context,
        content: str = None,
        timeout: int = 60,
        *,
        cancel_message: str = "Action cancelled.",
        **kwargs
    ) -> bool:
        view = cls(timeout, cancel_message=cancel_message)
        await view.send_initial_message(ctx, content, **kwargs)
        await view.wait()
        return view.value


class PageSource(ListPageSource):
    def __init__(self, pages: List[Any], per_page: int = 1):
        super().__init__(pages, per_page=per_page)

    async def format_page(self, view: discord.ui.View, page: Any):
        return page


class Button(discord.ui.Button):
    def __init__(
        self, label: str, style: discord.ButtonStyle = discord.ButtonStyle.blurple, **kwargs
    ):
        callback = kwargs.pop("callback")
        super().__init__(label=label, style=style, **kwargs)
        self._callback = callback

    async def callback(self, interaction: discord.Interaction):
        await self._callback(interaction, self)


class PaginatedView(BaseView):
    def __init__(self, source: PageSource, *, timeout: int = 60):
        super().__init__(timeout=timeout)
        self._source = source
        self.current_page = 0
        self._author_id: Optional[int] = None
        self.message: Optional[discord.Message] = None

        length = source.get_max_pages()
        if length > 2:
            self.add_item(Button("first", callback=self.first))
        if length > 1:
            self.add_item(Button("previous", callback=self.previous))
        self.add_item(Button("close", discord.ButtonStyle.red, callback=self.close))
        if length > 1:
            self.add_item(Button("next", callback=self.next))
        if length > 2:
            self.add_item(Button("last", callback=self.last))

    async def send_initial_message(self, ctx: commands.Context) -> discord.Message:
        self._author_id = ctx.author.id
        page = await self._source.get_page(self.current_page)
        kwargs = await self._get_kwargs_from_page(page)
        message = await ctx.reply(**kwargs)
        self.message = message
        return message

    async def _get_kwargs_from_page(self, page) -> dict:
        value = await discord.utils.maybe_coroutine(self._source.format_page, self, page)
        kwargs: Optional[dict] = None
        if isinstance(value, dict):
            kwargs = value
        elif isinstance(value, str):
            kwargs = {"content": value, "embed": None}
        elif isinstance(value, discord.Embed):
            kwargs = {"embed": value, "content": None}
        kwargs["view"] = self
        return kwargs

    async def show_page(self, page_number: int, interaction: discord.Interaction):
        page = await self._source.get_page(page_number)
        self.current_page = page_number
        kwargs = await self._get_kwargs_from_page(page)
        await interaction.response.edit_message(**kwargs)

    async def show_checked_page(self, page_number: int, interaction: discord.Interaction) -> None:
        max_pages = self._source.get_max_pages()
        try:
            if max_pages is None or max_pages > page_number >= 0:
                # If it doesn't give maximum pages, it cannot be checked
                await self.show_page(page_number, interaction)
            elif page_number >= max_pages:
                await self.show_page(0, interaction)
            else:
                await self.show_page(max_pages - 1, interaction)
        except IndexError:
            # An error happened that can be handled, so ignore it.
            pass

    async def first(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_checked_page(0, interaction)

    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_checked_page(self.current_page - 1, interaction)

    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        self.stop()

    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_checked_page(self.current_page + 1, interaction)

    async def last(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_checked_page(self._source.get_max_pages() - 1, interaction)

    async def on_timeout(self):
        self.disable_items()
        await self.message.edit(view=self)
