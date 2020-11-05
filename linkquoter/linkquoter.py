import re
from typing import Union

import discord
from redbot.core import Config, checks, commands
from redbot.core.commands.converter import BadArgument
from redbot.core.commands import Converter

link_regex = re.compile(
    r"https?:\/\/(?:(?:ptb|canary)\.)?discord(?:app)?\.com"
    r"\/channels\/(?P<guild_id>[0-9]{15,21})\/(?P<channel_id>"
    r"[0-9]{15,21})\/(?P<message_id>[0-9]{15,21})\/?"
)


def webhook_check(ctx: commands.Context) -> Union[bool, commands.Cog]:
    cog = ctx.bot.get_cog("Webhook")
    if (
        ctx.channel.permissions_for(ctx.me).manage_webhooks
        and cog
        and cog.__author__ == "PhenoM4n4n"
    ):
        return cog
    return False


class LinkToMessage(Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Message:
        match = re.search(link_regex, argument)
        if not match:
            raise BadArgument('Message "{}" not found.'.format(argument))

        channel_id = int(match.group("channel_id"))
        message_id = int(match.group("message_id"))

        message = ctx.bot._connection._get_message(message_id)
        if message:
            return await self.validate_message(ctx, message)

        channel = ctx.bot.get_channel(channel_id)
        if not channel:
            raise BadArgument('Channel "{}" not found.'.format(channel_id))
        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            raise BadArgument(argument)
        except discord.Forbidden:
            raise BadArgument("Can't read messages in {}.".format(channel.mention))
        else:
            return await self.validate_message(ctx, message)

    async def validate_message(
        self, ctx: commands.Context, message: discord.Message
    ) -> discord.Message:
        if not message.guild:
            raise BadArgument("I can only quote messages from servers.")
        guild = message.guild
        if message.channel.nsfw and not ctx.channel.nsfw:
            raise BadArgument("Messages from NSFW channels cannot be quoted in non-NSFW channels.")

        cog = ctx.bot.get_cog("LinkQuoter")
        data = await cog.config.guild(ctx.guild).all()

        if guild.id != ctx.guild.id:
            guild_data = await cog.config.guild(guild).all()
            if not data["cross_server"]:
                raise BadArgument(
                    f"This server is not opted in to quote messages from other servers."
                )
            elif not guild_data["cross_server"]:
                raise BadArgument(
                    f"That server is not opted in to allow its messages to be quoted in other servers."
                )

        member = guild.get_member(ctx.author.id)
        if member:
            author_perms = message.channel.permissions_for(member)
            if not (author_perms.read_message_history and author_perms.read_messages):
                raise BadArgument(f"You don't have permission to read messages in that channel.")
        return message


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
            "on": False,
            "webhooks": True,
            "cross_server": False,
            "respect_perms": False,
        }
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
                att = message.attachments[0]
                image = att.proxy_url
                e.add_field(name="Attachments", value=f"[{att.filename}]({att.url})")
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
    async def linkquote(self, ctx, message_link: LinkToMessage):
        """Quote a message from a link."""
        embeds = await self.create_embeds([message_link])
        if not embeds:
            return await ctx.send("Invalid link.")
        cog = webhook_check(ctx)
        if (await self.config.guild(ctx.guild).webhooks()) and cog:
            await cog.send_to_channel(
                ctx.channel,
                ctx.me,
                ctx.author,
                reason=f"For the {ctx.command.qualified_name} command",
                username=ctx.author.display_name,
                avatar_url=ctx.author.avatar_url,
                embed=embeds[0][0],
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

    @commands.admin_or_permissions(manage_guild=True)
    @linkquote.command(name="global")
    async def linkquote_global(self, ctx, true_or_false: bool = None):
        """
        Toggle cross-server quoting.

        Turning this setting on will allow this server to quote other servers, and other servers to quote this one.
        """
        target_state = (
            true_or_false
            if true_or_false is not None
            else not (await self.config.guild(ctx.guild).cross_server())
        )
        await self.config.guild(ctx.guild).cross_server.set(target_state)
        if target_state:
            await ctx.send(
                "This server is now opted in to cross-server quoting. "
                "This server can now quote other servers, and other servers can quote this one."
            )
        else:
            await ctx.send("This server is no longer opted in to cross-server quoting.")

    @commands.check(webhook_check)
    @commands.admin_or_permissions(manage_guild=True)
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

        ctx = commands.Context(
            message=message,
            author=message.author,
            guild=message.guild,
            channel=message.channel,
            me=message.guild.me,
            bot=self.bot,
            prefix="auto_linkquote",
            command=self.bot.get_command("linkquote"),
        )
        try:
            message = await LinkToMessage().convert(ctx, message.content)
        except BadArgument:
            return
        embeds = await self.create_embeds([message])
        if not embeds:
            return
        cog = webhook_check(ctx)
        if (await self.config.guild(ctx.guild).webhooks()) and cog:
            await cog.send_to_channel(
                ctx.channel,
                ctx.me,
                ctx.author,
                reason=f"For the {ctx.command.qualified_name} command",
                username=ctx.author.display_name,
                avatar_url=ctx.author.avatar_url,
                embed=embeds[0][0],
            )
        else:
            await ctx.send(embed=embeds[0][0])
