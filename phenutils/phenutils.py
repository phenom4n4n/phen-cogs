"""
MIT License

Copyright (c) 2020-2021 phenom4n4n

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import asyncio
import re
import time
from copy import copy
import re
import logging
from typing import Optional

import discord
from discord.utils import sleep_until
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands.converter import TimedeltaConverter
from redbot.core.config import Config

SLEEP_FLAG = re.compile(r"(?:--|—)sleep (\d+)$")


class PhenUtils(commands.Cog):
    """
    Various developer utilities.
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=623469945234523465,
            force_registration=True,
        )

    async def red_delete_data_for_user(self, *, requester: str, user_id: int) -> None:
        return

    @commands.is_owner()
    @commands.command()
    async def do(self, ctx, times: int, sequential: Optional[bool] = True, *, command: str):
        """
        Repeats a command a specified number of times.

        `--sleep <int>` is an optional flag specifying how much time to wait between command invocations.
        """
        if match := SLEEP_FLAG.search(command):  # too lazy to use argparse
            sleep = int(match.group(1))
            command = command[: -len(match.group(0))]
        else:
            sleep = 1

        new_message = copy(ctx.message)
        new_message.content = ctx.prefix + command.strip()
        if sequential:
            for _ in range(times):
                await self.bot.process_commands(new_message)
                await asyncio.sleep(sleep)
        else:
            todo = [self.bot.process_commands(new_message) for _ in range(times)]
            await asyncio.gather(*todo)

    @commands.is_owner()
    @commands.command()
    async def execute(self, ctx, sequential: Optional[bool] = False, *, commands):
        """Execute multiple commands at once. Split them using |."""
        commands = commands.split("|")
        if sequential:
            for command in commands:
                new_message = copy(ctx.message)
                new_message.content = ctx.prefix + command.strip()
                await self.bot.process_commands(new_message)
        else:
            todo = []
            for command in commands:
                new_message = copy(ctx.message)
                new_message.content = ctx.prefix + command.strip()
                todo.append(self.bot.process_commands(new_message))
            await asyncio.gather(*todo)

    @commands.is_owner()
    @commands.command()
    async def bypass(self, ctx, *, command):
        """Bypass a command's checks and cooldowns."""
        msg = copy(ctx.message)
        msg.content = ctx.prefix + command

        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        try:
            await new_ctx.reinvoke()
        except Exception as e:
            await ctx.send(embed=discord.Embed(title="Oops!", description=f"```\n{e}\n```"))

    @commands.is_owner()
    @commands.command()
    async def timing(self, ctx: commands.Context, *, command_string: str):
        """
        Run a command timing execution and catching exceptions.
        """
        msg = copy(ctx.message)
        msg.content = ctx.prefix + command_string
        alt_ctx = await self.bot.get_context(msg, cls=type(ctx))

        # alt_ctx = await copy_context_with(ctx, content=ctx.prefix + command_string)

        if alt_ctx.command is None:
            return await ctx.send(f'Command "{alt_ctx.invoked_with}" is not found')

        start = time.perf_counter()

        await alt_ctx.reinvoke()

        # async with ReplResponseReactor(ctx.message):
        #    with self.submit(ctx):
        #        await alt_ctx.command.invoke(alt_ctx)

        end = time.perf_counter()
        return await ctx.send(
            f"Command `{alt_ctx.command.qualified_name}` finished in {end - start:.3f}s."
        )

    @commands.is_owner()
    @commands.command(aliases=["taskcmd"])
    async def schedulecmd(self, ctx, time: TimedeltaConverter, *, command):
        """Schedule a command to be done later."""
        end = ctx.message.created_at + time
        new_message = copy(ctx.message)
        new_message.content = ctx.prefix + command.strip()
        await sleep_until(end)
        await self.bot.process_commands(new_message)

    @commands.is_owner()
    @commands.command()
    async def reinvoke(self, ctx: commands.Context, message: discord.Message = None):
        """
        Reinvoke a command message.

        You may reply to a message to reinvoke it or pass a message ID/link.
        """
        if not message:
            if hasattr(ctx.message, "reference") and (ref := ctx.message.reference):
                message = ref.resolved or await ctx.bot.get_channel(ref.channel_id).fetch_message(
                    ref.message_id
                )
            else:
                raise commands.BadArgument
        await self.bot.process_commands(message)

    @reinvoke.before_invoke
    async def reinvoke_before_invoke(self, ctx: commands.Context):
        if not ctx.guild.chunked:
            await ctx.guild.chunk()

    @commands.is_owner()
    @commands.command()
    async def loglevel(self, ctx: commands.Context, level: str.upper):
        """Set the log output level."""
        log = logging.getLogger("red")
        try:
            log.setLevel(level)
        except ValueError as exc:
            await ctx.send(exc)
        else:
            await ctx.send(f"Logging has been set to {level}.")
