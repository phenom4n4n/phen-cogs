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

# Remove command logic originally from: https://github.com/mikeshardmind/SinbadCogs/tree/v3/messagebox
# Speed test logic from https://github.com/PhasecoreX/PCXCogs/tree/master/netspeed

import asyncio
import concurrent
import datetime
import logging
import time

import discord
import speedtest
from redbot.core import Config, commands

old_ping = None
log = logging.getLogger("red.phenom4n4n.customping")


class CustomPing(commands.Cog):
    """A more information rich ping message."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=325236743863625234572,
            force_registration=True,
        )
        default_global = {"host_latency": True}
        self.config.register_global(**default_global)
        self.settings = {}

    async def initialize(self):
        self.settings = await self.config.all()

    async def red_delete_data_for_user(self, **kwargs):
        return

    def cog_unload(self):
        global old_ping
        if old_ping:
            try:
                self.bot.remove_command("ping")
            except:
                pass
            self.bot.add_command(old_ping)

    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(2, 5, commands.BucketType.user)
    @commands.group(invoke_without_command=True)
    async def ping(self, ctx):
        """View bot latency."""
        start = time.monotonic()
        message = await ctx.send("Pinging...")
        end = time.monotonic()
        totalPing = round((end - start) * 1000, 2)
        e = discord.Embed(title="Pinging..", description=f"Overall Latency: {totalPing}ms")
        await asyncio.sleep(0.25)
        try:
            await message.edit(content=None, embed=e)
        except discord.NotFound:
            return

        botPing = round(self.bot.latency * 1000, 2)
        e.description = e.description + f"\nDiscord WebSocket Latency: {botPing}ms"
        await asyncio.sleep(0.25)

        averagePing = (botPing + totalPing) / 2
        if averagePing >= 1000:
            color = discord.Colour.red()
        elif averagePing >= 200:
            color = discord.Colour.orange()
        else:
            color = discord.Colour.green()

        if not self.settings["host_latency"]:
            e.title = "Pong!"

        e.color = color
        try:
            await message.edit(embed=e)
        except discord.NotFound:
            return
        if not self.settings["host_latency"]:
            return

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        loop = asyncio.get_event_loop()
        try:
            s = speedtest.Speedtest(secure=True)
            await loop.run_in_executor(executor, s.get_servers)
            await loop.run_in_executor(executor, s.get_best_server)
        except Exception as exc:
            log.exception("An exception occured while fetching host latency.", exc_info=exc)
            host_latency = "`Failed`"
        else:
            result = s.results.dict()
            host_latency = round(result["ping"], 2)

        e.title = "Pong!"
        e.description = e.description + f"\nHost Latency: {host_latency}ms"
        await asyncio.sleep(0.25)
        try:
            await message.edit(embed=e)
        except discord.NotFound:
            return

    @ping.command()
    async def moreinfo(self, ctx: commands.Context):
        """Ping with additional latency stastics."""
        now = datetime.datetime.utcnow().timestamp()
        receival_ping = round((now - ctx.message.created_at.timestamp()) * 1000, 2)

        e = discord.Embed(
            title="Pinging..",
            description=f"Receival Latency: {receival_ping}ms",
        )

        send_start = time.monotonic()
        message = await ctx.send(embed=e)
        send_end = time.monotonic()
        send_ping = round((send_end - send_start) * 1000, 2)
        e.description += f"\nSend Latency: {send_ping}ms"
        await asyncio.sleep(0.25)

        edit_start = time.monotonic()
        try:
            await message.edit(embed=e)
        except discord.NotFound:
            return
        edit_end = time.monotonic()
        edit_ping = round((edit_end - edit_start) * 1000, 2)
        e.description += f"\nEdit Latency: {edit_ping}ms"

        average_ping = (receival_ping + send_ping + edit_ping) / 3
        if average_ping >= 1000:
            color = discord.Colour.red()
        elif average_ping >= 200:
            color = discord.Colour.orange()
        else:
            color = discord.Colour.green()

        e.color = color
        e.title = "Pong!"

        await asyncio.sleep(0.25)
        try:
            await message.edit(embed=e)
        except discord.NotFound:
            return

    @ping.command()
    async def shards(self, ctx: commands.Context):
        """View latency for all shards."""
        description = []
        latencies = []
        for shard_id, shard in self.bot.shards.items():
            latency = round(shard.latency * 1000, 2)
            latencies.append(latency)
            description.append(f"#{shard_id}: {latency}ms")
        average_ping = sum(latencies) / len(latencies)
        if average_ping >= 1000:
            color = discord.Colour.red()
        elif average_ping >= 200:
            color = discord.Colour.orange()
        else:
            color = discord.Colour.green()
        e = discord.Embed(color=color, title="Shard Pings", description="\n".join(description))
        e.set_footer(text=f"Average: {round(average_ping, 2)}ms")
        await ctx.send(embed=e)

    @commands.is_owner()
    @commands.group()
    async def pingset(self, ctx: commands.Context):
        """Manage CustomPing settings."""

    @pingset.command(name="hostlatency")
    async def pingset_hostlatency(self, ctx: commands.Context, true_or_false: bool = None):
        """Toggle displaying host latency on the ping command."""
        target_state = (
            true_or_false if true_or_false is not None else not (await self.config.host_latency())
        )
        await self.config.host_latency.set(target_state)
        self.settings["host_latency"] = target_state
        word = " " if target_state else " not "
        await ctx.send(
            f"Host latency will{word}be displayed on the `{ctx.clean_prefix}ping` command."
        )


async def setup(bot):
    global old_ping
    old_ping = bot.get_command("ping")
    if old_ping:
        bot.remove_command(old_ping.name)

    cog = CustomPing(bot)
    await cog.initialize()
    bot.add_cog(cog)
