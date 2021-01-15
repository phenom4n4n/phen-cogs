import re
from typing import Union, Optional, List, Tuple
import asyncio

import discord
from redbot.core import Config, checks, commands
from redbot.core.commands import Converter, BadArgument, MessageNotFound, ChannelNotFound

link_regex = re.compile(
    r"https?:\/\/(?:(?:ptb|canary)\.)?discord(?:app)?\.com"
    r"\/channels\/(?P<guild_id>[0-9]{15,19})\/(?P<channel_id>"
    r"[0-9]{15,19})\/(?P<message_id>[0-9]{15,19})\/?"
)


async def delete_quietly(ctx: commands.Context):
    if ctx.channel.permissions_for(ctx.me).manage_messages:
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass


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
            raise MessageNotFound(argument)

        channel_id = int(match.group("channel_id"))
        message_id = int(match.group("message_id"))

        message = ctx.bot._connection._get_message(message_id)
        if message:
            return await self.validate_message(ctx, message)

        channel = ctx.bot.get_channel(channel_id)
        if not channel or not channel.guild:
            raise ChannelNotFound(channel_id)

        my_perms = channel.permissions_for(channel.guild.me)
        if not my_perms.read_messages:
            raise BadArgument(f"Can't read messages in {channel.mention}.")
        elif not my_perms.read_message_history:
            raise BadArgument(f"Can't read message history in {channel.mention}.")

        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            raise MessageNotFound(argument)
        except discord.Forbidden:
            raise BadArgument(f"Can't read messages in {channel.mention}.")
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

    __version__ = "1.0.1"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\nCog Version: {self.__version__}"

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
            "delete": False,
        }
        self.config.register_guild(**default_guild)

        self.enabled_guilds = []
        self.task = asyncio.create_task(self.initialize())

    def cog_unload(self):
        if self.task:
            self.task.cancel()

    async def initialize(self):
        for guild_id, guild_data in (await self.config.all_guilds()).items():
            if guild_data["on"]:
                self.enabled_guilds.append(guild_id)

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

    async def message_to_embed(
        self,
        message: discord.Message,
        *,
        invoke_guild: discord.Guild = None,
        author_field: bool = True,
        footer_field: bool = True,
    ) -> Optional[discord.Embed]:
        image = None
        e: discord.Embed = None
        if message.embeds:
            embed = message.embeds[0]
            if str(embed.type) == "rich":
                if footer_field:
                    embed.timestamp = message.created_at
                e = embed
            if str(embed.type) in ("image", "article"):
                image = embed.url

        if not e:
            content = message.content
            e = discord.Embed(
                color=message.author.color,
                description=content,
                timestamp=message.created_at,
            )
        
        if author_field:
            e.set_author(
                name=f"{message.author} said..",
                icon_url=message.author.avatar_url,
                url=message.jump_url,
            )

        if footer_field:
            if invoke_guild and message.guild != invoke_guild:
                e.set_footer(
                    icon_url=message.guild.icon_url,
                    text=f"#{message.channel.name} | {message.guild}",
                )
            else:
                e.set_footer(text=f"#{message.channel.name}")

        if image:
            e.set_image(url=image)

        if message.attachments:
            att = message.attachments[0]
            image = att.proxy_url
            e.add_field(name="Attachments", value=f"[{att.filename}]({att.url})")

        if ref := message.reference:
            ref_message = ref.cached_message or (ref.resolved if ref.resolved and isinstance(ref.resolved, discord.Message) else None)
            if not ref_message:
                ref_chan = message.guild.get_channel(ref.channel_id)
                if ref_chan:
                    try:
                        ref_message = await ref_chan.fetch_message(ref.message_id)
                    except (discord.Forbidden, discord.NotFound):
                        pass
            if ref_message:
                jump_url = ref_message.jump_url
                e.add_field(
                    name="Replying to",
                    value=f"[{ref_message.content[:1000] if ref_message.content else 'Click to view attachments'}]({jump_url})",
                    inline=False,
                )

        e.add_field(
            name="Source",
            value=f'\n[[jump to message]]({message.jump_url} "Follow me to the original message!")',
            inline=False,
        )
        return e

    async def create_embeds(self, 
        messages: list, 
        *, 
        invoke_guild: discord.Guild = None,
        author_field: bool = True,
        footer_field: bool = True,
    ) -> List[Tuple[discord.Embed, discord.Member]]:
        embeds = []
        for message in messages:
            embed = await self.message_to_embed(message, invoke_guild=invoke_guild, author_field=author_field, footer_field=footer_field)
            if embed:
                embeds.append((embed, message.author))
        return embeds

    @commands.cooldown(3, 15, type=commands.BucketType.channel)
    @commands.guild_only()
    @commands.command(aliases=["linkmessage"])
    async def linkquote(self, ctx, message_link: LinkToMessage = None):
        """Quote a message from a link."""
        if not message_link:
            if hasattr(ctx.message, "reference") and (ref := ctx.message.reference):
                message_link = ref.resolved or await ctx.bot.get_channel(
                    ref.channel_id
                ).fetch_message(ref.message_id)
            else:
                raise commands.BadArgument
        cog = webhook_check(ctx)
        if (await self.config.guild(ctx.guild).webhooks()) and cog:
            embed = await self.message_to_embed(message_link, invoke_guild=ctx.guild, author_field=False)
            await cog.send_to_channel(
                ctx.channel,
                ctx.me,
                ctx.author,
                reason=f"For the {ctx.command.qualified_name} command",
                username=ctx.author.display_name,
                avatar_url=ctx.author.avatar_url,
                embed=embed,
            )
        else:
            embed = await self.message_to_embed(message_link, invoke_guild=ctx.guild)
            await ctx.send(embed=embed)

    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group()
    async def linkquoteset(self, ctx: commands.Context):
        """Manage LinkQuoter settings."""

    @linkquoteset.command(name="auto")
    async def linkquoteset_auto(self, ctx, true_or_false: bool = None):
        """
        Toggle automatic link-quoting.

        Enabling this will make [botname] attempt to quote any message link that is sent in this server.
        [botname] will ignore any message that has "no quote" in it.
        If the user doesn't have permission to view the channel that they link, it will not quote.

        To enable quoting from other servers, run `[p]linkquoteset global`.
        """
        target_state = (
            true_or_false
            if true_or_false is not None
            else not (await self.config.guild(ctx.guild).on())
        )
        await self.config.guild(ctx.guild).on.set(target_state)
        if target_state:
            await ctx.send("I will now automatically quote links.")
            if ctx.guild.id not in self.enabled_guilds:
                self.enabled_guilds.append(ctx.guild.id)
        else:
            await ctx.send("I will no longer automatically quote links.")
            if ctx.guild.id in self.enabled_guilds:
                self.enabled_guilds.pop(self.enabled_guilds.index(ctx.guild.id))

    @linkquoteset.command(name="delete")
    async def linkquoteset_delete(self, ctx, true_or_false: bool = None):
        """
        Toggle deleting of messages for automatic quoting.

        If automatic quoting is enabled, then [botname] will also delete messages that contain links in them.
        """
        target_state = (
            true_or_false
            if true_or_false is not None
            else not (await self.config.guild(ctx.guild).delete())
        )
        await self.config.guild(ctx.guild).delete.set(target_state)
        if target_state:
            await ctx.send("I will now delete messages when automatically quoting.")
        else:
            await ctx.send("I will no longer delete messages when automatically quoting.")

    @linkquoteset.command(name="global")
    async def linkquoteset_global(self, ctx, true_or_false: bool = None):
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
    @checks.bot_has_permissions(manage_webhooks=True)
    @linkquoteset.command(name="webhook")
    async def linkquoteset_webhook(self, ctx, true_or_false: bool = None):
        """
        Toggle whether [botname] should use webhooks to quote.

        [botname] must have Manage Webhook permissions to use webhooks when quoting.
        """
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

    @linkquoteset.command(name="settings")
    async def linkquoteset_settings(self, ctx: commands.Context):
        """View LinkQuoter settings."""
        data = await self.config.guild(ctx.guild).all()
        description = [
            f"**Automatic Quoting:** {data['on']}",
            f"**Cross-Server:** {data['cross_server']}",
            f"**Delete Messages:** {data['delete']}",
            f"**Use Webhooks:** {data['webhooks']}",
        ]
        e = discord.Embed(color=await ctx.embed_color(), description="\n".join(description))
        e.set_author(name=f"{ctx.guild} LinkQuoter Settings", icon_url=ctx.guild.icon_url)
        await ctx.send(embed=e)

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot or isinstance(message.author, discord.User):
            return
        if not message.guild:
            return
        guild: discord.Guild = message.guild
        if guild.id not in self.enabled_guilds:
            return
        if not await self.bot.message_eligible_as_command(message):
            return
        guild: discord.Guild = message.guild
        if "no quote" in message.content.lower():
            return
        channel: discord.TextChannel = message.channel

        ctx = commands.Context(
            message=message,
            author=message.author,
            guild=guild,
            channel=channel,
            me=message.guild.me,
            bot=self.bot,
            prefix="auto_linkquote",
            command=self.bot.get_command("linkquote"),
        )
        try:
            message = await LinkToMessage().convert(ctx, message.content)
        except BadArgument:
            return
        cog = webhook_check(ctx)
        data = await self.config.guild(ctx.guild).all()
        tasks = []
        if cog and data["webhooks"]:
            embed = await self.message_to_embed(message, invoke_guild=ctx.guild, author_field=False)
            tasks.append(
                cog.send_to_channel(
                    ctx.channel,
                    ctx.me,
                    ctx.author,
                    reason=f"For the {ctx.command.qualified_name} command",
                    username=ctx.author.display_name,
                    avatar_url=ctx.author.avatar_url,
                    embed=embed,
                )
            )
        else:
            embed = await self.message_to_embed(message, invoke_guild=ctx.guild)
            tasks.append(ctx.send(embed=embed))
        if data["delete"]:
            tasks.append(delete_quietly(ctx))
        await asyncio.gather(*tasks)
