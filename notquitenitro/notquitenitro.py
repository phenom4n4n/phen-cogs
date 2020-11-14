import re
from typing import Literal

import discord
from discord.ext import tasks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

EMOJI_RE = re.compile(r"\B:([a-zA-Z0-9\_]+):\B")


class NotQuiteNitro(commands.Cog):
    """
    Use custom emojis anywhere! It's not quite nitro...
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=462364255128256513,
            force_registration=True,
        )
        default_guild = {
            "opted_to_emojis": True,
        }
        defalt_global = {
            "opted_guilds": [],
        }
        self.config.register_guild(**default_guild)
        self.config.register_global(**defalt_global)
        self.allowed_mentions = discord.AllowedMentions(users=True, roles=False, everyone=False)
        self.opted_guilds = []
        # self.emojis = []
        # self.recache.start()

    # def cog_unload(self):
    # self.recache.cancel()

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        return

    async def initialize(self):
        await self.bot.wait_until_ready()
        opted_guilds = await self.config.opted_guilds()
        self.opted_guilds = opted_guilds
        # all_guild_data = await self.config.all_guilds()
        # for guild in self.bot.guilds:
        #     guild_data = all_guild_data.get(guild.id, {"opted_to_emojis": True})
        #     if guild_data["opted_to_emojis"] and guild.emojis:
        #         self.emojis.extend(guild.emojis)

    # @tasks.loop(seconds=60)
    # async def recache(self):
    #     await self.initialize()

    @commands.guild_only()
    @commands.group(invoke_without_command=True, aliases=["nqn"])
    async def notquitenitro(self, ctx, emojis: commands.Greedy[discord.Emoji]):
        """Use emojis from any server! It's not quite nitro..."""
        if not emojis:
            raise commands.BadArgument
        message = "".join([str(emoji) for emoji in emojis])
        await ctx.send(message)

    @commands.admin_or_permissions(manage_guild=True)
    @notquitenitro.command()
    async def auto(self, ctx: commands.Context):
        """Toggle automatic NQN."""
        _id = ctx.guild.id
        async with self.config.opted_guilds() as o:
            if _id in o:
                o.pop(o.index(_id))
                msg = "Automatic NQN has been turned off."
            else:
                o.append(_id)
                msg = "Automatic NQN has been turned on."
        await ctx.send(msg)
        self.opted_guilds = o

    # @commands.admin_or_permissions(manage_guild=True)
    # @notquitenitro.command()
    async def optemojis(self, ctx: commands.Context, true_or_false: bool = None):
        """
        Opt in to allow NotQuiteNitro to use this server's emojis.

        By default this server is opted in, however if you would not like other servers with NotQuiteNitro enabled to use this server's emojis, you may opt out with this command.
        NotQuiteNitro will continue to work on this server.
        """
        target_state = (
            true_or_false
            if true_or_false is not None
            else not (await self.config.guild(ctx.guild).opted_to_emojis())
        )
        await self.config.guild(ctx.guild).opted_to_emojis.set(target_state)
        if target_state:
            await ctx.send(
                "Other servers will now be able to use this server's emojis with NotQuiteNitro."
            )
            await self.initialize()
        else:
            await ctx.send(
                "Other servers will no longer be able to use this server's emojis with NotQuiteNitro."
            )
            await self.initialize()

    @commands.is_owner()
    @notquitenitro.command(name="message", aliases=["msg"])
    async def nqn_msg(self, ctx: commands.Context, message: discord.Message):
        """Send a message with nqn emojis."""
        if not message.content:
            raise commands.BadArgument

        def content_to_emoji(content: re.Match) -> str:
            emoji_name = content.group(1)
            emoji = discord.utils.get(
                ctx.guild.emojis, name=emoji_name, available=True
            ) or discord.utils.get(self.bot.emojis, name=emoji_name, available=True)
            if emoji:
                return str(emoji)
            else:
                return f":{emoji_name}:"

        newcontent = re.sub(EMOJI_RE, content_to_emoji, message.content)
        await ctx.send(newcontent)

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot or not message.guild or not message.content:
            return
        guild: discord.Guild = message.guild
        if guild.id not in self.opted_guilds:
            return
        channel: discord.TextChannel = message.channel
        my_perms: discord.Permissions = channel.permissions_for(guild.me)
        if not my_perms.send_messages:
            return
        author: discord.Member = message.author

        def content_to_emoji(content: re.Match) -> str:
            emoji_name = content.group(1)
            emoji = discord.utils.get(
                guild.emojis, name=emoji_name, available=True
            ) or discord.utils.get(self.bot.emojis, name=emoji_name, available=True)
            if emoji:
                return str(emoji)
            else:
                return f":{emoji_name}:"

        if not re.search(EMOJI_RE, message.content):
            return
        newcontent = re.sub(EMOJI_RE, content_to_emoji, message.content)
        if newcontent == message.content:
            return
        if my_perms.manage_messages:
            try:
                await message.delete()
            except discord.HTTPException:
                pass
        if my_perms.manage_webhooks and (cog := self.bot.get_cog("Webhook")):
            await cog.send_to_channel(
                channel,
                guild.me,
                author,
                content=newcontent,
                avatar_url=author.avatar_url,
                username=author.display_name,
                allowed_mentions=self.allowed_mentions,
            )
        else:
            await channel.send(newcontent)
