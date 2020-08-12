import discord

from redbot.core import commands, Config, checks

from redbot.core.bot import Red
import asyncio

class AllowedMentions(commands.Cog):
    """
    Adjust mention settings.
    """
    def __init__(self, bot: "Red"):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9532427562145697, force_registration=True)
        default_global = {
            "everyone": False,
            "roles": False,
            "users": True
            }

        self.config.register_global(**default_global)
        bot.allowed_mentions = discord.AllowedMentions(everyone=False, roles=False)
    
    @checks.is_owner()
    @commands.command()
    async def allowedmentions(self, ctx, value, true_or_false: bool):
        pass