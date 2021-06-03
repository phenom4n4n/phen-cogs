import asyncio
import logging
from typing import List, Union

import discord
from redbot.core import commands
from redbot.vendored.discord.ext import menus

from ..http import Button, ButtonStyle, Component, InteractionButton

__all__ = ("PageSource", "ButtonMenu", "BaseButtonMenu", "menu", "ButtonMenuMixin")

log = logging.getLogger("red.phenom4n4n.slashtags.testing.button_menus")

REWIND_ARROW = "⏪"
LEFT_ARROW = "⬅️"
CLOSE_EMOJI = "❌"
RIGHT_ARROW = "➡️"
FORWARD_ARROW = "⏩"


def chunks(l, n):
    """
    Yield successive n-sized chunks from l.
    from https://github.com/flaree/flare-cogs/blob/bf629ec6d8c28519bf08256b2f5132a216d1671e/commandstats/commandstats.py#L17
    """
    for i in range(0, len(l), n):
        yield l[i : i + n]


class PageSource(menus.ListPageSource):
    def __init__(self, pages: list):
        super().__init__(pages, per_page=1)

    def is_paginating(self):
        return True

    async def format_page(self, menu: menus.MenuPages, page: Union[discord.Embed, str]):
        return page


class MenuButton(menus.Button):
    __slots__ = ("style",)

    def __init__(self, emoji, action, *, style: ButtonStyle = ButtonStyle.blurple, **kwargs):
        super().__init__(emoji, action, **kwargs)
        self.style = style


class ButtonMenuMixin:
    def __init__(self, *args, **kwargs):
        # kwargs["clear_reactions_after"] = False
        self.custom_id = kwargs.pop("custom_id", None)
        super().__init__(*args, **kwargs)
        self._buttons_closed = True
        self._components = []

    @property
    def __tasks(self):
        return self._Menu__tasks

    def _get_component_from_emoji(self, emoji: discord.PartialEmoji) -> Button:
        return Button(style=ButtonStyle.grey, custom_id=f"{self.custom_id}-{emoji}", emoji=emoji)

    def _get_components(self) -> List[Component]:
        components = []
        for emojis in chunks(list(self.buttons.keys()), 5):
            buttons = [self._get_component_from_emoji(emoji) for emoji in emojis]
            components.append(Component(components=buttons))
        return components

    async def _send(
        self,
        ctx: commands.Context,
        content: str = None,
        *,
        embed: discord.Embed = None,
        reference: discord.MessageReference = None,
        mention_author: bool = False,
    ) -> discord.Message:
        components = self._get_components()
        channel = ctx.channel
        data = {"components": [c.to_dict() for c in components]}
        if content:
            data["content"] = str(content)
        if embed:
            data["embed"] = embed.to_dict()
        if reference:
            data["message_reference"] = reference.to_dict()
        allowed_mentions = channel._state.allowed_mentions.to_dict()
        allowed_mentions["replied_user"] = mention_author
        data["allowed_mentions"] = allowed_mentions

        log.debug("sending data %r" % data)
        r = discord.http.Route("POST", "/channels/{channel_id}/messages", channel_id=channel.id)
        response = await self.bot._connection.http.request(r, json=data)
        self._buttons_closed = False
        return channel._state.create_message(channel=channel, data=response)

    def reaction_check(self, button: InteractionButton) -> bool:
        raw_message = button._original_data["message"]
        if int(raw_message["id"]) != self.message.id:
            return False
        if button.author_id not in {self.bot.owner_id, self._author_id, *self.bot.owner_ids}:
            asyncio.create_task(button.send("You cannot use this menu.", hidden=True))
            return False
        return button.custom_id.startswith(self.custom_id)

    async def start(self, ctx, *, channel=None, wait=False):
        # Clear the buttons cache and re-compute if possible.
        try:
            del self.buttons
        except AttributeError:
            pass

        self.bot = bot = ctx.bot
        self.ctx = ctx
        self._author_id = ctx.author.id
        channel = channel or ctx.channel
        is_guild = isinstance(channel, discord.abc.GuildChannel)
        me = ctx.guild.me if is_guild else ctx.bot.user
        permissions = channel.permissions_for(me)
        self.__me = discord.Object(id=me.id)
        self._verify_permissions(ctx, channel, permissions)
        self._event.clear()
        msg = self.message
        if msg is None:
            self.message = msg = await self.send_initial_message(ctx, channel)

        if self.should_add_reactions():
            # Start the task first so we can listen to reactions before doing anything
            for task in self.__tasks:
                task.cancel()
            self.__tasks.clear()

            self._running = True
            self.__tasks.append(bot.loop.create_task(self._internal_loop()))

            # self.__tasks.append(bot.loop.create_task(add_reactions_task()))

            if wait:
                await self._event.wait()

    async def _internal_loop(self):
        try:
            self.__timed_out = False
            loop = self.bot.loop
            # Ensure the name exists for the cancellation handling
            tasks = []
            while self._running:
                tasks = [
                    asyncio.create_task(
                        self.bot.wait_for("button_interaction", check=self.reaction_check)
                    ),
                ]
                done, pending = await asyncio.wait(
                    tasks, timeout=self.timeout, return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()

                if len(done) == 0:
                    raise asyncio.TimeoutError()

                # Exception will propagate if e.g. cancelled or timed out
                payload = done.pop().result()
                loop.create_task(self.update(payload))

                # NOTE: Removing the reaction ourselves after it's been done when
                # mixed with the checks above is incredibly racy.
                # There is no guarantee when the MESSAGE_REACTION_REMOVE event will
                # be called, and chances are when it does happen it'll always be
                # after the remove_reaction HTTP call has returned back to the caller
                # which means that the stuff above will catch the reaction that we
                # just removed.

                # For the future sake of myself and to save myself the hours in the future
                # consider this my warning.

        except asyncio.TimeoutError:
            self.__timed_out = True
        finally:
            self._event.set()

            # Cancel any outstanding tasks (if any)
            for task in tasks:
                task.cancel()

            try:
                await self.finalize(self.__timed_out)
            except Exception:
                pass
            finally:
                self.__timed_out = False

            # Can't do any requests if the bot is closed
            if self.bot.is_closed():
                return

            # Wrap it in another block anyway just to ensure
            # nothing leaks out during clean-up
            try:
                if self.delete_message_after:
                    return await self.message.delete()

                if self.clear_reactions_after:
                    return await self.close_buttons()

            except Exception:
                pass

    def _get_emoji(self, button: InteractionButton):
        emoji_string = button.custom_id[len(self.custom_id) + 1 :]
        return menus._cast_emoji(emoji_string)

    async def update(self, payload: InteractionButton):
        button = self.buttons[self._get_emoji(payload)]
        if not button:
            return
        if not self._running:
            return

        try:
            if button.lock:
                async with self._lock:
                    if self._running:
                        await button(self, payload)
            else:
                await button(self, payload)
        except Exception as error:
            log.exception(
                f"An error occured while updating {type(self).__name__} menu.", exc_info=error
            )

    async def _edit_message_components(self, components: List[Component]):
        route = discord.http.Route(
            "PATCH",
            "/channels/{channel_id}/messages/{message_id}",
            channel_id=self.message.channel.id,
            message_id=self.message.id,
        )
        data = {"components": [c.to_dict() for c in components]}
        await self.bot._connection.http.request(route, json=data)


class BaseButtonMenu(ButtonMenuMixin, menus.MenuPages, inherit_buttons=False):
    async def show_checked_page(self, page_number: int, button: InteractionButton):
        max_pages = self._source.get_max_pages()
        try:
            if max_pages is None or page_number < max_pages and page_number >= 0:
                # If it doesn't give maximum pages, it cannot be checked
                await self.show_page(page_number, button)
            elif page_number >= max_pages:
                await self.show_page(0, button)
            else:
                await self.show_page(max_pages - 1, button)
        except IndexError:
            # An error happened that can be handled, so ignore it.
            pass

    async def show_page(
        self, page_number: int, button: InteractionButton, *, recalculate_components: bool = True
    ):
        page = await self._source.get_page(page_number)
        self.current_page = page_number
        kwargs = await self._get_kwargs_from_page(page)
        if recalculate_components:
            kwargs["components"] = self._get_components()
        await button.update(**kwargs)

    async def send_initial_message(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel,
        *,
        reply: bool = False,
        mention_author: bool = False,
    ):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        if not self.custom_id:
            self.custom_id = str(ctx.message.id)
        if reply:
            kwargs["reference"] = ctx.message.to_reference(fail_if_not_exists=False)
            kwargs["mention_author"] = mention_author
        return await self._send(ctx, **kwargs)

    async def _edit_button_components(
        self, button: InteractionButton, components: List[Component]
    ):
        page = await self._source.get_page(self.current_page)
        kwargs = await self._get_kwargs_from_page(page)
        kwargs["components"] = components
        await button.update(**kwargs)

    async def close_buttons(self, button: InteractionButton = None):
        if self._buttons_closed:
            return
        if button:
            page = await self._source.get_page(self.current_page)
            kwargs = await self._get_kwargs_from_page(page)
            await button.update(**kwargs, components=[])
        else:
            await self._edit_message_components([])
        self._buttons_closed = True

    async def change_source(self, source: menus.PageSource, button: InteractionButton):
        if not isinstance(source, menus.PageSource):
            raise TypeError("Expected {0!r} not {1.__class__!r}.".format(PageSource, source))

        self._source = source
        self.current_page = 0
        if self.message is not None:
            await source._prepare_once()
            await self.show_page(0, button)

    def add_button(self, button, *, react=False, interaction: InteractionButton = None):
        self._buttons[button.emoji] = button

        if react:
            if self.__tasks:

                async def wrapped():
                    # Add the component
                    self.buttons[button.emoji] = button
                    components = self._get_components()
                    if interaction:
                        await self._edit_button_components(interaction, components)
                    else:
                        await self._edit_message_components(components)

                return wrapped()

            async def dummy():
                raise menus.MenuError("Menu has not been started yet")

            return dummy()


class ButtonMenu(BaseButtonMenu, inherit_buttons=False):
    def _skip_single_arrows(self):
        max_pages = self._source.get_max_pages()
        if max_pages is None:
            return True
        return max_pages == 1

    def _skip_double_triangle_buttons(self):
        max_pages = self._source.get_max_pages()
        if max_pages is None:
            return True
        return max_pages <= 2

    @menus.button(
        LEFT_ARROW,
        position=menus.First(1),
        skip_if=_skip_single_arrows,
    )
    async def go_to_previous_page(self, button: InteractionButton):
        await self.show_checked_page(self.current_page - 1, button)

    @menus.button(
        RIGHT_ARROW,
        position=menus.Last(0),
        skip_if=_skip_single_arrows,
    )
    async def go_to_next_page(self, button: InteractionButton):
        await self.show_checked_page(self.current_page + 1, button)

    @menus.button(
        REWIND_ARROW,
        position=menus.First(0),
        skip_if=_skip_double_triangle_buttons,
    )
    async def go_to_first_page(self, button: InteractionButton):
        await self.show_checked_page(0, button)

    @menus.button(
        FORWARD_ARROW,
        position=menus.Last(1),
        skip_if=_skip_double_triangle_buttons,
    )
    async def go_to_last_page(self, button: InteractionButton):
        await self.show_checked_page(self._source.get_max_pages() - 1, button)

    @menus.button(CLOSE_EMOJI)
    async def stop_pages(self, button: InteractionButton):
        await self.message.delete()
        # if self.clear_reactions_after:
        #    await self.close_buttons(button)
        self.stop()


async def menu(
    ctx: commands.Context,
    pages: List[Union[str, discord.Embed]],
    controls: dict = None,
    *,
    timeout: int = 60,
):
    # eat controls arg if passed
    source = PageSource(pages)
    button_menu = ButtonMenu(source, timeout=timeout, clear_reactions_after=True)
    await button_menu.start(ctx)
