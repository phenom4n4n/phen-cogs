import discord
import re

from redbot.core import commands, checks, Config

r = re.compile(r"https://(?:canary\.|ptb\.)?discord(?:app)?\.com/channels/\d{17,19}/\d{17,19}/\d{17,19}")

class LinkQuoter(commands.Cog):
    """
    Quote Discord message links.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=6234567898747434823,
            force_registration=True,
        )

        default_guild = {
            "on": False
            }
        self.config.register_guild(**default_guild)

    async def regex_check(self, content: str):
        return r.findall(content)

    async def get_messages(self, guild: discord.Guild, links: list):
        messages = []
        for link in links:
            link_segments = link.split("/")
            link_ids = []
            for segment in link_segments[-3:]:
                try:
                    link_ids.append(int(segment))
                except ValueError:
                    return
            if link_ids[0] != guild.id:
                return
            channel = guild.get_channel(link_ids[1])
            if not channel:
                return
            if not channel.permissions_for(guild.me).read_messages:
                return
            try:
                message = await channel.fetch_message(link_ids[2])
                messages.append(message)
            except discord.errors.NotFound:
                return
        return messages

    async def create_embeds(self, messages: list):
        embeds = []
        for message in messages:
            if not message.content:
                return
            e = discord.Embed(
                color=message.author.color,
                description=message.content,
                timestamp=message.created_at
            )
            e.set_author(name=f"{message.author} said..", icon_url=message.author.avatar_url)
            e.set_footer(text=f"#{message.channel.name}")
            embeds.append((e, message.author))
        return embeds

    @commands.group(invoke_without_command=True)
    async def linkquote(self, ctx, link: str):
        links = await self.regex_check(link)
        if not links:
            return await ctx.send("Invalid link.")
        messages = await self.get_messages(ctx.guild, links)
        if not messages:
            return await ctx.send("Invalid link.")
        embeds = await self.create_embeds(messages)
        if ctx.channel.permissions_for(ctx.guild.me).manage_webhooks:
            webhooks = await ctx.channel.webhooks()
            if webhooks:
                await webhooks[0].send(embed=embeds[0][0], username=embeds[0][1].display_name, avatar_url=embeds[0][1].avatar_url)
            else:
                webhook = await ctx.channel.create_webhook(name=f"{self.bot.user} Webhook")
                await webhook.send(embed=embeds[0][0], username=embeds[0][1].display_name, avatar_url=embeds[0][1].avatar_url)
        else:
            await ctx.send(embed=embeds[0][0])
    
    @linkquote.command()
    async def toggle(self, ctx, true_or_false: bool=None):
        """Toggle automatic quoting."""
        
        target_state = (
            true_or_false
            if true_or_false is not None
            else not (await self.config.guild(ctx.guild).on())
        )
        await self.config.guild(ctx.guild).on.set(target_state)
        if target_state:
            await ctx.send("I will now automatically quote links.")
        else:
            await ctx.send("I will no longer automatically quote links.")

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot or not message.guild or not message.channel.permissions_for(message.guild.me).send_messages:
            return

        if not await self.config.guild(message.guild).on():
            return

        links = await self.regex_check(message.content)
        if not links:
            return
        messages = await self.get_messages(message.guild, links)
        if not messages:
            return
        embeds = await self.create_embeds(messages)
        if message.channel.permissions_for(message.guild.me).manage_webhooks:
            webhooks = await message.channel.webhooks()
            if webhooks:
                await webhooks[0].send(embed=embeds[0][0], username=embeds[0][1].display_name, avatar_url=embeds[0][1].avatar_url)
            else:
                webhook = await message.channel.create_webhook(name=f"{self.bot.user} Webhook")
                await webhook.send(embed=embeds[0][0], username=embeds[0][1].display_name, avatar_url=embeds[0][1].avatar_url)
        else:
            await message.channel.send(embed=embeds[0][0])