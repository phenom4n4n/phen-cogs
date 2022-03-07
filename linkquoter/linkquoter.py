"""
MIT License

Copyright (c) 2020-present phenom4n4n

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import asyncio
import logging
from typing import List, Optional, Tuple, Union

import discord
from redbot.core import Config, checks, commands

from .converters import LinkToMessage

log = logging.getLogger("red.phenom4n4n.linkquoter")

COOLDOWN = (3, 10, commands.BucketType.channel)


def webhook_check(ctx: commands.Context) -> Union[bool, commands.Cog]:
    if not ctx.channel.permissions_for(ctx.me).manage_webhooks:
        raise commands.UserFeedbackCheckFailure(
            "I need the **Manage Webhooks** permission for webhook quoting."
        )
    cog = ctx.bot.get_cog("Webhook")
    if cog and cog.__author__ == "PhenoM4n4n":
        return cog
    raise commands.UserFeedbackCheckFailure(
        "The Webhook cog by PhenoM4n4n must be loaded for webhook quoting."
    )


class LinkQuoter(commands.Cog):
    """
    Quote Discord message links.
    """

    __version__ = "1.2.0"

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

        self.enabled_guilds = set()
        self.task = asyncio.create_task(self.initialize())
        self.spam_control = commands.CooldownMapping.from_cooldown(*COOLDOWN)

    def cog_unload(self):
        if self.task:
            self.task.cancel()

    async def initialize(self):
        for guild_id, guild_data in (await self.config.all_guilds()).items():
            if guild_data["on"]:
                self.enabled_guilds.add(guild_id)

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
            if not channel or channel.is_nsfw():
                continue
            author_perms = channel.permissions_for(author)
            if not (author_perms.read_messages and author_perms.read_message_history):
                continue
            my_perms = channel.permissions_for(guild.me)
            if not (my_perms.read_messages and my_perms.read_message_history):
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
            embed = message.embeds[0].copy()
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
                icon_url=message.author.display_avatar.url,
                url=message.jump_url,
            )

        if footer_field:
            if invoke_guild and message.guild != invoke_guild:
                e.set_footer(
                    icon_url=message.guild.icon.url,
                    text=f"#{message.channel.name} | {message.guild}",
                )
            else:
                e.set_footer(text=f"#{message.channel.name}")

        if message.attachments:
            att = message.attachments[0]
            image = att.proxy_url
            e.add_field(name="Attachments", value=f"[{att.filename}]({att.url})", inline=False)

        if not image and (stickers := getattr(message, "stickers", [])):
            for sticker in stickers:
                if sticker.image_url:
                    image = str(sticker.image_url)
                    e.add_field(name="Stickers", value=f"[{sticker.name}]({image})", inline=False)
                    break

        if image:
            e.set_image(url=image)

        if ref := message.reference:
            ref_message = ref.cached_message or (
                ref.resolved
                if ref.resolved and isinstance(ref.resolved, discord.Message)
                else None
            )
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

    async def create_embeds(
        self,
        messages: list,
        *,
        invoke_guild: discord.Guild = None,
        author_field: bool = True,
        footer_field: bool = True,
    ) -> List[Tuple[discord.Embed, discord.Member]]:
        embeds = []
        for message in messages:
            embed = await self.message_to_embed(
                message,
                invoke_guild=invoke_guild,
                author_field=author_field,
                footer_field=footer_field,
            )
            if embed:
                embeds.append((embed, message.author))
        return embeds

    @commands.cooldown(*COOLDOWN)
    @commands.guild_only()
    @commands.command(aliases=["linkmessage"])
    async def linkquote(self, ctx: commands.Context, message_link: LinkToMessage = None):
        """Quote a message from a link."""
        if not message_link:
            if not (ref := ctx.message.reference):
                raise commands.BadArgument
            message_link = ref.resolved or await ctx.guild.get_channel(
                ref.channel_id
            ).fetch_message(ref.message_id)
        cog = webhook_check(ctx)
        if (await self.config.guild(ctx.guild).webhooks()) and cog:
            embed = await self.message_to_embed(
                message_link, invoke_guild=ctx.guild, author_field=False
            )
            await cog.send_to_channel(
                ctx.channel,
                ctx.me,
                ctx.author,
                reason=f"For the {ctx.command.qualified_name} command",
                username=message_link.author.display_name,
                avatar_url=message_link.author.display_avatar.url,
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

        To prevent spam, links can be automatically quoted 3 times every 10 seconds.
        """
        target_state = (
            true_or_false
            if true_or_false is not None
            else not (await self.config.guild(ctx.guild).on())
        )
        await self.config.guild(ctx.guild).on.set(target_state)
        if target_state:
            await ctx.send("I will now automatically quote links.")
            self.enabled_guilds.add(ctx.guild.id)
        else:
            await ctx.send("I will no longer automatically quote links.")
            self.enabled_guilds.remove(ctx.guild.id)

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
        e.set_author(name=f"{ctx.guild} LinkQuoter Settings", icon_url=ctx.guild.icon.url)
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
        guild: discord.Guild = message.guild
        if "no quote" in message.content.lower():
            return
        channel = message.channel

        bucket = self.spam_control.get_bucket(message)
        current = message.created_at.timestamp()
        retry_after = bucket.get_retry_after(current)
        if retry_after:
            log.debug("%r ratelimits exhausted, retry after: %s", channel, retry_after)
            return

        ctx = commands.Context(
            message=message,
            bot=self.bot,
            view=None,
            prefix="[auto-linkquote]",
            command=self.bot.get_command("linkquote"),
        )
        try:
            quoted_message = await LinkToMessage().convert(ctx, message.content)
        except commands.BadArgument:
            return

        if not await self.bot.message_eligible_as_command(message):
            return

        try:
            cog = webhook_check(ctx)
        except commands.CheckFailure:
            cog = False

        data = await self.config.guild(ctx.guild).all()
        tasks = []
        if cog and data["webhooks"] and channel.type == discord.ChannelType.text:
            embed = await self.message_to_embed(
                quoted_message, invoke_guild=ctx.guild, author_field=False
            )
            tasks.append(
                cog.send_to_channel(
                    ctx.channel,
                    ctx.me,
                    ctx.author,
                    reason=f"For the {ctx.command.qualified_name} command",
                    username=quoted_message.author.display_name,
                    avatar_url=quoted_message.author.display_avatar.url,
                    embed=embed,
                )
            )
        else:
            embed = await self.message_to_embed(quoted_message, invoke_guild=ctx.guild)
            tasks.append(channel.send(embed=embed))
        if data["delete"]:
            tasks.append(self.delete_quietly(ctx))
        await asyncio.gather(*tasks)

        bucket.update_rate_limit(current)

    @staticmethod
    async def delete_quietly(ctx: commands.Context):
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass
