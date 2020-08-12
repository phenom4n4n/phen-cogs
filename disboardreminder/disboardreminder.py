# Bump restart logic taken from https://github.com/Redjumpman/Jumper-Plugins/tree/V3/raffle
import discord
import calendar
from datetime import datetime

from redbot.core import Config, checks, commands

from redbot.core.bot import Red
import asyncio

class DisboardReminder(commands.Cog):
    """
    Set a reminder to bump on Disboard.
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.load_check = self.bot.loop.create_task(self.bump_worker())
        self.config = Config.get_conf(self, identifier=9765573181940385953309, force_registration=True)
        default_guild = {
            "channel": None,
            "role": None,
            "message": "It's been 2 hours since the last successful bump, could someone run `!d bump`?",
            "nextBump": None
        }

        self.config.register_guild(**default_guild)

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group()
    async def bumpreminder(self, ctx):
        """Set a reminder to bump on Disboard.
        
        This sends a reminder to bump in a specified channel 2 hours after someone successfully bumps, thus making it more accurate than a repeating schedule."""

    @bumpreminder.command()
    async def channel(self, ctx, channel: discord.TextChannel=None):
        """Set the channel to send bump reminders to.

        This also works as a toggle, so if no channel is provided, it will disable reminders for this server."""

        if channel is None:
            await self.config.guild(ctx.guild).channel.clear()
            await ctx.send("Disabled bump reminders in this server.")
        else:
            try:
                await channel.send("Set this channel as the reminder channel for bumps. "
                                   "I will not send my first reminder until a successful bump is registered.")
                await self.config.guild(ctx.guild).channel.set(channel.id)
            except discord.errors.Forbidden:
                await ctx.send("I do not have permission to talk in that channel.")
        await ctx.tick()
    
    @checks.has_permissions(mention_everyone=True)
    @bumpreminder.command()
    async def pingrole(self, ctx, role: discord.Role=None):
        """Set a role to ping for bump reminders. If no role is provided, it will clear the current role."""

        if role is None:
            await self.config.guild(ctx.guild).role.clear()
            await ctx.send("Cleared the role for bump reminders.")
        else:
            await ctx.send(f"Set {role.name} to ping for bump reminders.")
            await self.config.guild(ctx.guild).role.set(role.id)
    
    @bumpreminder.command()
    async def message(self, ctx, *, message: str = None):
        """Change the message used for reminders. Providing no message will reset to the default message."""

        if message:
            await self.config.guild(ctx.guild).message.set(message)
            await ctx.tick()
        else:
            await self.config.guild(ctx.guild).message.clear()
            await ctx.send("Reset this serer's reminder message.")
    
    async def bump_timer(self, guild: discord.Guild, remaining: int):
        await asyncio.sleep(remaining)
        await self.bump_message(guild)
    
    async def bump_message(self, guild: discord.Guild):
        data = await self.config.guild(guild).all()
        channel = guild.get_channel(data["channel"])
        if data["role"]:
            role = guild.get_role(data["role"])
            message = data["message"]
            message = f"{role.mention}: {message}"
        else:
            message = data["message"]
        mentionPerms = discord.AllowedMentions(roles=True)
        await channel.send(message, allowed_mentions=mentionPerms)
        await self.config.guild(guild).nextBump.clear()

# this doesn't actually work.. pls help
    async def bump_worker(self):
        """Restarts bump timers
        This worker will attempt to restart bump timers incase of a cog reload or
        if the bot has been restart or shutdown. The task is only created when the cog
        is loaded, and is destroyed when it has finished.
        """
        try:
            await self.bot.wait_until_ready()
            print("bump worker activated")
            guilds = [self.bot.get_guild(guild) for guild in await self.config.all_guilds()]
            print(guilds)
            coros = []
            for guild in guilds:
                print(guild)
                timer = await self.config.guild(guild).nextBump()
                if timer:
                    print(timer)
                    now = calendar.timegm(datetime.utcnow().utctimetuple())
                    remaining = timer - now
                    if remaining <= 0:
                        await self.bump_message(guild)
                    else:
                        coros.append(self.bump_timer(guild, remaining))
            await asyncio.gather(*coros)
        except Exception as e:
            print(e)

    def cog_unload(self):
        self.__unload()

    def __unload(self):
        self.load_check.cancel()

    @commands.Cog.listener("on_message_without_command")
    async def disboard_remind(self, message):
        if message.guild is None:
            return

        if message.author.id != 302050872383242240:
            return

        data = await self.config.guild(message.guild).all()

        if data["channel"] is None:
            return

        if not message.embeds:
            return
        embed = message.embeds[0]
        if "Bump done" not in embed.description:
            return
        
        channel = message.channel
        
        cmdMessages = await channel.history(limit=10).flatten()
        cmdMessage = discord.utils.find(lambda m: m.content.lower().startswith("!d bump") and m.author.id in embed.description, cmdMessages)
        if cmdMessage:
            await channel.send(f"{cmdMessage.author.mention}, thank you for bumping! I will send my next reminder in 2 hours.")

        nextBump = calendar.timegm(message.created_at.utctimetuple()) + 7200
        await self.config.guild(message.guild).nextBump.set(nextBump)

        await self.bump_timer(message.guild, 7200)