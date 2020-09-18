import typing
from copy import copy
import time
import asyncio
import datetime
import discord
from discord.utils import sleep_until

from redbot.core import commands, checks
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.commands.converter import TimedeltaConverter

RequestType = typing.Literal["discord_deleted_user", "owner", "user", "user_strict"]


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

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        return

    @checks.is_owner()
    @commands.command()
    async def do(self, ctx, times: int, *, command):
        """Repeats a command a specified number of times."""
        msg = copy(ctx.message)
        msg.content = ctx.prefix + command

        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        # new_ctx._db = ctx._db

        try:
            for i in range(times):
                await new_ctx.reinvoke()
                await asyncio.sleep(1)
        except Exception as e:
            await ctx.send(embed=discord.Embed(title="Oops!", description=f"```\n{e}\n```"))

    @checks.is_owner()
    @commands.command()
    async def execute(self, ctx, sequential: typing.Optional[bool] = False, *, commands):
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

    @checks.is_owner()
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

    @checks.is_owner()
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

    @checks.is_owner()
    @commands.command(aliases=["taskcmd"])
    async def schedulecmd(self, ctx, time: TimedeltaConverter, *, command):
        """Schedule a command to be done later."""
        end = ctx.message.created_at + time
        new_message = copy(ctx.message)
        new_message.content = ctx.prefix + command.strip()
        await sleep_until(end)
        await self.bot.process_commands(new_message)