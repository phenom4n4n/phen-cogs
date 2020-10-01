import discord
import re

from redbot.core import commands, checks, Config

r = re.compile(
    r"https://(?:canary\.|ptb\.)?discord(?:app)?\.com/channels/\d{17,19}/\d{17,19}/\d{17,19}"
)


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

        default_guild = {"on": False, "webhooks": True}
        self.config.register_guild(**default_guild)

    async def regex_check(self, content: str):
        return r.findall(content)

    async def get_messages(self, guild: discord.Guild, author: discord.Member, links: list):
        messages = []
        for link in links:
            link_segments = link.split("/")
            link_ids = []
            for segment in link_segments[-3:]:
                try:
                    link_ids.append(int(segment))
                except ValueError:
                    continue
            if link_ids[0] != guild.id:
                continue
            channel = guild.get_channel(link_ids[1])
            if (
                not channel
                or channel.is_nsfw()
                or not channel.permissions_for(member).read_messages
            ):
                continue
            if not (
                channel.permissions_for(guild.me).read_messages
                and channel.permissions_for(guild.me).read_message_history
            ):
                continue
            try:
                message = await channel.fetch_message(link_ids[2])
                messages.append(message)
            except discord.errors.NotFound:
                continue
        return messages

    async def create_embeds(self, messages: list):
        embeds = []
        for message in messages:
            image = False
            e = False
            if message.embeds:
                embed = message.embeds[0]
                if str(embed.type) == "rich":
                    embed.color = message.author.color
                    embed.timestamp = message.created_at
                    embed.set_author(
                        name=f"{message.author} said..",
                        icon_url=message.author.avatar_url,
                        url=message.jump_url,
                    )
                    embed.set_footer(text=f"#{message.channel.name}")
                    e = embed
                if str(embed.type) == "image" or str(embed.type) == "article":
                    image = embed.url
            elif not message.content and not message.embeds and not message.attachments:
                return
            if not e:
                content = message.content
                e = discord.Embed(
                    color=message.author.color,
                    description=content,
                    timestamp=message.created_at,
                )
                e.set_author(
                    name=f"{message.author} said..",
                    icon_url=message.author.avatar_url,
                    url=message.jump_url,
                )
                e.set_footer(text=f"#{message.channel.name}")
            if message.attachments:
                image = message.attachments[0].proxy_url
                e.add_field(name="Attachments", value=message.attachments[0].filename)
            if image:
                e.set_image(url=image)
            e.add_field(
                name="Source",
                value=f'\n[`[jump to message]`]({message.jump_url} "Follow me to the original message!")',
                inline=False,
            )
            embeds.append((e, message.author))
        return embeds

    @commands.cooldown(3, 15, type=commands.BucketType.channel)
    @commands.guild_only()
    @commands.group(invoke_without_command=True, aliases=["linkmessage"])
    async def linkquote(self, ctx, link: str):
        """Quote a message from a link."""
        await ctx.trigger_typing()
        links = await self.regex_check(link)
        if not links:
            return await ctx.send("Invalid link.")
        messages = await self.get_messages(ctx.guild, ctx.author, links)
        if not messages:
            return await ctx.send("Invalid link.")
        embeds = await self.create_embeds(messages)
        if not embeds:
            return await ctx.send("Invalid link.")
        if (await self.config.guild(ctx.guild).webhooks()) and ctx.channel.permissions_for(
            ctx.guild.me
        ).manage_webhooks:
            webhooks = await ctx.channel.webhooks()
            if webhooks:
                await webhooks[0].send(
                    embed=embeds[0][0],
                    username=embeds[0][1].display_name,
                    avatar_url=embeds[0][1].avatar_url,
                )
            else:
                webhook = await ctx.channel.create_webhook(name=f"{self.bot.user} Webhook")
                await webhook.send(
                    embed=embeds[0][0],
                    username=embeds[0][1].display_name,
                    avatar_url=embeds[0][1].avatar_url,
                )
        else:
            await ctx.send(embed=embeds[0][0])

    @linkquote.command()
    async def auto(self, ctx, true_or_false: bool = None):
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

    @checks.bot_has_permissions(manage_webhooks=True)
    @linkquote.command()
    async def webhook(self, ctx, true_or_false: bool = None):
        """Toggle whether the bot should use webhooks to quote."""

        target_state = (
            true_or_false
            if true_or_false is not None
            else not (await self.config.guild(ctx.guild).webhooks())
        )
        await self.config.guild(ctx.guild).webhooks.set(target_state)
        if target_state:
            await ctx.send("I will now use webhooks to quote.")
        else:
            await ctx.send("I will no longer use webhooks to quote.")

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot or not (
            message.guild and await self.bot.message_eligible_as_command(message)
        ):
            return

        if not await self.config.guild(message.guild).on():
            return

        links = await self.regex_check(message.content)
        if not links:
            return
        messages = await self.get_messages(message.guild, message.author, links)
        if not messages:
            return
        embeds = await self.create_embeds(messages)
        if not embeds:
            return
        if (await self.config.guild(message.guild).webhooks()) and message.channel.permissions_for(
            message.guild.me
        ).manage_webhooks:
            webhooks = await message.channel.webhooks()
            if webhooks:
                await webhooks[0].send(
                    embed=embeds[0][0],
                    username=embeds[0][1].display_name,
                    avatar_url=embeds[0][1].avatar_url,
                )
            else:
                webhook = await message.channel.create_webhook(name=f"{self.bot.user} Webhook")
                await webhook.send(
                    embed=embeds[0][0],
                    username=embeds[0][1].display_name,
                    avatar_url=embeds[0][1].avatar_url,
                )
        else:
            await message.channel.send(embed=embeds[0][0])
