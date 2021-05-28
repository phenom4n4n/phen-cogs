import asyncio
import logging
from typing import List, Union

import discord
from redbot.core import commands
from redbot.vendored.discord.ext import menus

from ..http import Button, ButtonStyle, Component, InteractionButton

__all__ = ("PageSource", "ButtonMenu", "BaseButtonMenu", "menu")

log = logging.getLogger("red.phenom4n4n.slashtags.testing.button_menus")

REWIND_ARROW = "⏪"
LEFT_ARROW = "⬅️"
CLOSE_EMOJI = "❌"
RIGHT_ARROW = "➡️"
FORWARD_ARROW = "⏩"


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


class BaseButtonMenu(menus.MenuPages, inherit_buttons=False):
    def __init__(self, source: menus.PageSource, *, custom_id: str = None, **kwargs):
        # kwargs["clear_reactions_after"] = False
        super().__init__(source, **kwargs)
        self.custom_id = custom_id
        self._buttons_closed = True

    @property
    def __tasks(self):
        return self._Menu__tasks

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

    async def show_page(self, page_number: int, button: InteractionButton):
        page = await self._source.get_page(page_number)
        self.current_page = page_number
        kwargs = await self._get_kwargs_from_page(page)
        await button.update(**kwargs)

    async def send_initial_message(self, ctx: commands.Context, channel: discord.TextChannel):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        if not self.custom_id:
            self.custom_id = str(ctx.message.id)
        return await self.send(channel, **kwargs)

    def _get_components(self) -> List[Button]:
        return [
            Button(
                style=ButtonStyle.grey,
                custom_id=f"{self.custom_id}-{emoji}",
                emoji=emoji,
            )
            for emoji in self.buttons
        ]

    async def send(
        self, channel: discord.TextChannel, content: str = None, *, embed: discord.Embed = None
    ) -> discord.Message:
        buttons = self._get_components()
        components = Component(components=buttons)

        data = {"components": [components.to_dict()]}
        if content:
            data["content"] = content
        if embed:
            data["embed"] = embed.to_dict()

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

    async def close_buttons(self, button: InteractionButton = None):
        if self._buttons_closed:
            return
        if button:
            page = await self._source.get_page(self.current_page)
            kwargs = await self._get_kwargs_from_page(page)
            await button.update(**kwargs, components=[])
        else:
            route = discord.http.Route(
                "PATCH",
                "/channels/{channel_id}/messages/{message_id}",
                channel_id=self.message.channel.id,
                message_id=self.message.id,
            )
            data = {"components": []}
            await self.bot._connection.http.request(route, json=data)
        self._buttons_closed = True

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
