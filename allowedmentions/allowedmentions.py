import discord

from redbot.core import commands

from redbot.core.bot import Red
import asyncio

class AllowedMentions(commands.Cog):
    """
    Adjust mention settings.
    """

    def __init__(self, bot: Red):
        bot.allowed_mentions = discord.AllowedMentions(everyone=False, roles=False)