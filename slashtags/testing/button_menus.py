import asyncio
import logging
from typing import List, Union

import discord
from redbot.core import commands
from redbot.vendored.discord.ext import menus

from ..http import Button, Component, InteractionButton

__all__ = ("PageSource", "ButtonMenu", "menu")

log = logging.getLogger("red.phenom4n4n.slashtags.testing.button_menus")

LEFT_ARROW = "⬅️"
CLOSE_EMOJI = "❌"
RIGHT_ARROW = "➡️"

LEFT = "-left"
CLOSE = "close"
RIGHT = "right"

id_emojis = {"-left": LEFT_ARROW, "close": CLOSE_EMOJI, "right": RIGHT_ARROW}


def _get_emoji(custom_id: str):
    return discord.PartialEmoji(name=id_emojis[custom_id[-5:]])


class PageSource(menus.ListPageSource):
    def __init__(self, pages: list):
        super().__init__(pages, per_page=1)

    def is_paginating(self):
        return True

    async def format_page(self, menu: menus.MenuPages, page: Union[discord.Embed, str]):
        return page


class ButtonMenu(menus.MenuPages, inherit_buttons=False):
    def __init__(self, source: menus.PageSource, *, custom_id: str = None, **kwargs):
        kwargs["clear_reactions_after"] = False
        super().__init__(source, **kwargs)
        self.custom_id = custom_id

    @property
    def __tasks(self):
        return self._Menu__tasks

    @menus.button(LEFT_ARROW)
    async def go_to_previous_page(self, button: InteractionButton):
        await self.show_checked_page(self.current_page - 1, button)

    @menus.button(CLOSE_EMOJI)
    async def stop_pages(self, button: InteractionButton):
        await self.close_buttons(button)
        self.stop()

    @menus.button(RIGHT_ARROW)
    async def go_to_next_page(self, button: InteractionButton):
        """go to the next page"""
        await self.show_checked_page(self.current_page + 1, button)

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
        self.custom_id = str(ctx.message.id)
        return await self.send(channel, **kwargs)

    async def send(
        self, channel: discord.TextChannel, content: str = None, *, embed: discord.Embed = None
    ) -> discord.Message:
        r = discord.http.Route("POST", "/channels/{channel_id}/messages", channel_id=channel.id)
        left_button = Button(style=1, custom_id=f"{self.custom_id}-{LEFT}", emoji=LEFT_ARROW)
        close_button = Button(style=4, custom_id=f"{self.custom_id}-{CLOSE}", emoji=CLOSE_EMOJI)
        right_button = Button(style=1, custom_id=f"{self.custom_id}-{RIGHT}", emoji=RIGHT_ARROW)
        components = Component(components=[left_button, close_button, right_button])

        data = {"components": [components.to_dict()]}
        if content:
            data["content"] = content
        if embed:
            data["embed"] = embed.to_dict()

        log.debug("sending data %r" % data)
        response = await self.bot._connection.http.request(r, json=data)
        return channel._state.create_message(channel=channel, data=response)

    def reaction_check(self, button: InteractionButton):
        raw_message = button._original_data["message"]
        if int(raw_message["id"]) != self.message.id:
            return False
        if button.author_id not in {self.bot.owner_id, self._author_id, *self.bot.owner_ids}:
            return False

        return button.custom_id.startswith(self.custom_id)

    async def close_buttons(self, button: InteractionButton):
        page = await self._source.get_page(self.current_page)
        kwargs = await self._get_kwargs_from_page(page)
        await button.update(**kwargs, components=[])

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

            async def add_reactions_task():
                for emoji in self.buttons:
                    await msg.add_reaction(emoji)

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
                    if self._can_remove_reactions:
                        return await self.message.clear_reactions()

                    for button_emoji in self.buttons:
                        try:
                            await self.message.remove_reaction(button_emoji, self.__me)
                        except discord.HTTPException:
                            continue
            except Exception:
                pass

    async def update(self, payload):
        button = self.buttons[_get_emoji(payload.custom_id)]
        if not self._running:
            return

        try:
            if button.lock:
                async with self._lock:
                    if self._running:
                        await button(self, payload)
            else:
                await button(self, payload)
        except Exception:
            # TODO: logging?
            import traceback

            traceback.print_exc()


async def menu(
    ctx: commands.Context, pages: List[Union[str, discord.Embed]], *, timeout: int = 60
):
    source = PageSource(pages)
    button_menu = ButtonMenu(source, timeout=timeout)
    await button_menu.start(ctx)
