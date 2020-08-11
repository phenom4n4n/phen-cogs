import discord
import time
import asyncio
import concurrent
import speedtest

from redbot.core import commands, checks

old_ping = None


class CustomPing(commands.Cog):
    """A more information rich ping message."""

    __author__ = "phenom4n4n"

    def __init__(self, bot):
        self.bot = bot

    def cog_unload(self):
        global old_ping
        if old_ping:
            try:
                self.bot.remove_command("ping")
            except:
                pass
            self.bot.add_command(old_ping)

    @checks.bot_has_permissions(embed_links=True)
    @commands.cooldown(5, 10, commands.BucketType.user)
    @commands.command()
    async def ping(self, ctx):
        """Ping the bot..."""
        start = time.perf_counter()
        message = await ctx.send("Pinging...")
        end = time.perf_counter()
        totalPing = round((end - start) * 1000, 2)

        botPing = round(self.bot.latency * 1000, 2)

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        loop = asyncio.get_event_loop()
        s = speedtest.Speedtest(secure=True)
        await loop.run_in_executor(executor, s.get_servers)
        await loop.run_in_executor(executor, s.get_best_server)
        result = s.results.dict()
        hostPing = round(result["ping"], 2)

        averagePing = (botPing + totalPing) / 2
        if averagePing >= 1000:
            color = discord.Colour.red()
        elif averagePing >= 200:
            color = discord.Colour.orange()
        else:
            color = discord.Colour.green()

        e = discord.Embed(
            color=color,
            title="Pong!",
            description=f"Overall Command Latency: {totalPing}ms\nDiscord WebSocket Latency: {botPing}ms\nHost Latency: {hostPing}ms"
        )
        await message.edit(content=None, embed=e)

def setup(bot):
    ping = CustomPing(bot)
    global old_ping
    old_ping = bot.get_command("ping")
    if old_ping:
        bot.remove_command(old_ping.name)
    bot.add_cog(ping)
