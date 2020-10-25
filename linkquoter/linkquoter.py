import re

import discord
from redbot.core import Config, checks, commands
from redbot.core.commands.converter import BadArgument, Converter

link_regex = re.compile(
    r'^https?://(?:(ptb|canary)\.)?discord(?:app)?\.com/channels/'
    r'(?:[0-9]{15,21})'
    r'/(?P<channel_id>[0-9]{15,21})/(?P<message_id>[0-9]{15,21})/?$'
)

class LinkToEmbed(Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        match = re.match(link_regex, argument)
        if not match:
            raise BadArgument('Message "{}" not found.'.format(argument))
        message_id = int(match.group("message_id"))
        channel_id = match.group("channel_id")
        message = ctx.bot._connection._get_message(message_id)
        if message:
            return message
        channel = ctx.bot.get_channel(int(channel_id)) if channel_id else ctx.channel
        if not channel:
            raise BadArgument('Channel "{}" not found.'.format(channel_id))
        try:
            return await channel.fetch_message(message_id)
        except discord.NotFound:
            raise BadArgument(argument)
        except discord.Forbidden:
            raise BadArgument("Can't read messages in {}.".format(channel.mention))

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

        default_guild = {"on": False, "webhooks": True, "cross_server": False, "respect_perms": False}
        self.config.register_guild(**default_guild)


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
                or not (
                    channel.permissions_for(author).read_messages
                    and channel.permissions_for(author).read_message_history
                )
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
                value=f'\n[[jump to message]]({message.jump_url} "Follow me to the original message!")',
                inline=False,
            )
            embeds.append((e, message.author))
        return embeds

    @commands.cooldown(3, 15, type=commands.BucketType.channel)
    @commands.guild_only()
    @commands.group(invoke_without_command=True, aliases=["linkmessage"])
    async def linkquote(self, ctx, message_link: LinkToEmbed):
        """Quote a message from a link."""
        await ctx.trigger_typing()
        messages = await self.get_messages(ctx.guild, ctx.author, message_link)
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

        links = regex_check(message.content)
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
