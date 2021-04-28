"""
MIT License

Copyright (c) 2020-2021 phenom4n4n

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
from typing import Dict, Optional, Union

import aiohttp
import discord
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import humanize_list, pagify
from redbot.core.utils.menus import (DEFAULT_CONTROLS, close_menu, menu,
                                     start_adding_reactions)
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate

from .converters import WebhookLinkConverter
from .errors import InvalidWebhook, WebhookNotMatched
from .session import Session
from .utils import USER_MENTIONS, WEBHOOK_RE, FakeResponse, _monkeypatch_send


class Webhook(commands.Cog):
    """Webhook utility commands."""

    __author__ = "PhenoM4n4n"

    __version__ = "1.2.0"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=2352346345723453463,
            force_registration=True,
        )
        self.config.register_global(monkey_patch=False)

        self.webhook_sessions: Dict[int, Session] = {}
        self.channel_cache: Dict[int, discord.Webhook] = {}
        self.link_cache: Dict[int, discord.Webhook] = {}
        self.session = aiohttp.ClientSession()

        self.old_send = commands.Context.send
        self._monkey_patched = False

    async def initialize(self):
        data = await self.config.all()
        if data["monkey_patch"]:
            self._apply_monkeypatch()

    def cog_unload(self):
        asyncio.create_task(self.session.close())
        self._remove_monkeypatch()

    async def red_delete_data_for_user(self, **kwargs):
        return

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\nCog Version: {self.__version__}"

    @staticmethod
    async def delete_quietly(ctx: commands.Context):
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass

    @commands.guild_only()
    @commands.group()
    async def webhook(self, ctx):
        """Webhook related commands."""

    @commands.bot_has_permissions(manage_webhooks=True)
    @commands.admin_or_permissions(manage_webhooks=True)
    @webhook.command()
    async def create(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel = None,
        *,
        webhook_name: str = None,
    ):
        """Creates a webhook in the channel specified with the name specified.

        If no channel is specified then it will default to the current channel."""
        channel = channel or ctx.channel
        webhook_name = webhook_name or f"{ctx.bot.user.name} Webhook"
        creation_reason = f"Webhook creation requested by {ctx.author} ({ctx.author.id})"
        await channel.create_webhook(name=webhook_name, reason=creation_reason)
        await ctx.tick()

    @commands.admin_or_permissions(manage_webhooks=True)
    @webhook.command()
    async def send(
        self, ctx: commands.Context, webhook_link: WebhookLinkConverter, *, message: str
    ):
        """Sends a message to the specified webhook using your avatar and display name."""
        await self.webhook_link_send(
            webhook_link,
            username=ctx.author.display_name,
            avatar_url=ctx.author.avatar_url,
            content=message,
        )

    @commands.bot_has_permissions(manage_webhooks=True)
    @webhook.command()
    async def say(self, ctx: commands.Context, *, message: str):
        """Sends a message to the channel as a webhook with your avatar and display name."""
        await self.delete_quietly(ctx)
        await self.send_to_channel(
            ctx.channel,
            ctx.me,
            ctx.author,
            ctx=ctx,
            content=message,
            avatar_url=ctx.author.avatar_url,
            username=ctx.author.display_name,
        )

    @commands.admin_or_permissions(manage_webhooks=True)
    @commands.bot_has_permissions(manage_webhooks=True)
    @webhook.command()
    async def sudo(self, ctx: commands.Context, member: discord.Member, *, message: str):
        """Sends a message to the channel as a webhook with the specified member's avatar and display name."""
        await self.delete_quietly(ctx)
        await self.send_to_channel(
            ctx.channel,
            ctx.me,
            ctx.author,
            ctx=ctx,
            content=message,
            avatar_url=member.avatar_url,
            username=member.display_name,
        )

    @commands.admin_or_permissions(manage_webhooks=True, manage_guild=True)
    @commands.bot_has_permissions(manage_webhooks=True)
    @webhook.command(hidden=True)
    async def loudsudo(self, ctx: commands.Context, member: discord.Member, *, message: str):
        """Sends a message to the channel as a webhook with the specified member's avatar and display name."""
        await self.send_to_channel(
            ctx.channel,
            ctx.me,
            ctx.author,
            ctx=ctx,
            content=message,
            avatar_url=member.avatar_url,
            username=member.display_name,
            allowed_mentions=USER_MENTIONS,
        )

    @commands.admin_or_permissions(manage_webhooks=True, manage_guild=True)
    @commands.bot_has_permissions(manage_webhooks=True)
    @webhook.command(hidden=True)
    async def clyde(self, ctx: commands.Context, *, message: str):
        """Sends a message to the channel as a webhook with Clyde's avatar and name."""
        await self.delete_quietly(ctx)
        await self.send_to_channel(
            ctx.channel,
            ctx.me,
            ctx.author,
            ctx=ctx,
            content=message,
            avatar_url="https://discordapp.com/assets/f78426a064bc9dd24847519259bc42af.png",
            username="C​I​​​​​​y​d​e",
            allowed_mentions=USER_MENTIONS,
        )

    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.has_permissions(manage_webhooks=True)
    @commands.bot_has_permissions(manage_webhooks=True)
    @webhook.command()
    async def clear(self, ctx):
        """Delete all webhooks in the server."""
        webhooks = await ctx.guild.webhooks()
        if not webhooks:
            await ctx.send("There are no webhooks in this server.")
            return

        msg = await ctx.send(
            "This will delete all webhooks in the server. Are you sure you want to do this?"
        )
        start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
        pred = ReactionPredicate.yes_or_no(msg, ctx.author)
        try:
            await ctx.bot.wait_for("reaction_add", check=pred, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send("Action Cancelled.")
            return

        if pred.result is False:
            return await ctx.send("Action Cancelled.")
        msg = await ctx.send("Deleting webhooks..")
        count = 0
        async with ctx.typing():
            for webhook in webhooks:
                try:
                    await webhook.delete(
                        reason=f"Guild Webhook Deletion requested by {ctx.author} ({ctx.author.id})"
                    )
                except discord.InvalidArgument:
                    pass
                else:
                    count += 1
        try:
            await msg.edit(content=f"{count} webhooks deleted.")
        except discord.NotFound:
            await ctx.send(f"{count} webhooks deleted.")

    @commands.mod_or_permissions(ban_members=True)
    @webhook.command(name="permissions", aliases=["perms"])
    async def webhook_permissions(self, ctx: commands.Context):
        """Show all members in the server that have `manage_webhook` permissions."""
        async with ctx.typing():
            roles = []
            lines = []
            total_members = set()

            for role in ctx.guild.roles:
                perms = role.permissions
                if perms.administrator or perms.manage_webhooks:
                    roles.append(role)
                    lines.append(f"**{role}** | {role.mention}")
                    members = []
                    for member in filter(lambda m: m not in total_members, role.members):
                        total_members.add(member)
                        member_string = f"{member} ({member.id})"
                        if member.bot:
                            member_string = f"[{member_string}](https://www.youtube.com/watch?v=dQw4w9WgXcQ&ab_channel=RickAstleyVEVO 'This user is a bot')"
                        members.append(member_string)
                    if members:
                        lines.append(humanize_list(members))

            if not lines:
                await ctx.send(
                    "No one here has `manage_webhook` permissions other than the owner."
                )

            base_embed = discord.Embed(
                color=await ctx.embed_color(), title="Users with `manage_webhook` Permissions"
            )
            base_embed.set_footer(text=f"{len(roles)} roles | {len(total_members)} members")
            embeds = []

            for page in pagify("\n".join(lines)):
                embed = base_embed.copy()
                embed.description = page
                embeds.append(embed)

        controls = {"\N{CROSS MARK}": close_menu} if len(embeds) == 1 else DEFAULT_CONTROLS
        await menu(ctx, embeds, controls)

    @commands.max_concurrency(1, commands.BucketType.channel)
    @commands.admin_or_permissions(manage_webhooks=True)
    @webhook.group(name="session", invoke_without_command=True)
    async def webhook_session(self, ctx: commands.Context, webhook_link: WebhookLinkConverter):
        """Initiate a session within this channel sending messages to a specified webhook link."""
        if ctx.channel.id in self.webhook_sessions:
            return await ctx.send(
                f"This channel already has an ongoing session. Use `{ctx.clean_prefix}webhook session close` to close it."
            )
        session = Session(self, channel=ctx.channel, author=ctx.author, webhook=webhook_link)
        await session.initialize(ctx)

    @webhook_session.command(name="close")
    async def webhook_session_close(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ):
        """Close an ongoing webhook session in a channel."""
        channel = channel or ctx.channel
        session = self.webhook_sessions.get(channel.id)
        if not session:
            return await ctx.send(
                f"This channel does not have an ongoing webhook session. Start one with `{ctx.clean_prefix}webhook session`."
            )
        await session.close()

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        author: discord.Member = message.author
        if author.bot:
            return
        channel: discord.TextChannel = message.channel
        try:
            session: Session = self.webhook_sessions[channel.id]
        except KeyError:
            return
        await session.send(
            message.content,
            embeds=message.embeds,
            username=author.display_name,
            avatar_url=author.avatar_url,
            allowed_mentions=USER_MENTIONS,
        )

    @commands.cooldown(5, 10, commands.BucketType.guild)
    @commands.admin_or_permissions(manage_webhooks=True)
    @webhook.command(name="edit")
    async def webhook_edit(self, ctx: commands.Context, message: discord.Message, *, content: str):
        """Edit a message sent by a webhook."""
        if not message.webhook_id:
            raise commands.BadArgument
        if not message.channel.permissions_for(ctx.me).manage_webhooks:
            return await ctx.send(f"I need `Manage Webhook` permission in {message.channel}.")
        webhooks = await message.channel.webhooks()
        webhook = None
        for chan_webhook in webhooks:
            if (
                chan_webhook.type == discord.WebhookType.incoming
                and chan_webhook.id == message.webhook_id
            ):
                webhook = chan_webhook
                break
        if not webhook:
            raise commands.BadArgument
        await webhook.edit_message(message.id, content=content)
        await self.delete_quietly(ctx)

    def _apply_monkeypatch(self):
        if not self._monkey_patched:
            commands.Context.send = self._webhook_monkeypatch_send
            self._monkey_patched = True

    def _remove_monkeypatch(self):
        if self._monkey_patched:
            commands.Context.send = self.old_send
            self._monkey_patched = False

    @property
    def _webhook_monkeypatch_send(self):
        return _monkeypatch_send

    @commands.is_owner()
    @webhook.command(name="monkeypatch", hidden=True)
    async def webhook_monkeypatch(self, ctx: commands.Context, true_or_false: bool = None):
        """
        Monkeypatch `commands.Context.send` to use webhooks.

        Don't run this if you don't know what monkeypatch means.
        """
        target_state = (
            true_or_false if true_or_false is not None else not (await self.config.monkey_patch())
        )
        await self.config.monkey_patch.set(target_state)
        if target_state:
            self._apply_monkeypatch()
            await ctx.send("Command responses will use webhooks.")
        else:
            self._remove_monkeypatch()
            await ctx.send("Command responses will be sent normally.")

    def get_webhook_from_link(
        self, link: Union[discord.Webhook, int, str]
    ) -> Optional[discord.Webhook]:
        if isinstance(link, int):
            return self.link_cache.get(link)
        elif isinstance(link, discord.Webhook):
            if link.id not in self.link_cache:
                self.link_cache[link.id] = link
            return link
        else:
            match = WEBHOOK_RE.search(link)
            if not match:
                raise WebhookNotMatched("That doesn't look like a webhook link.")

            webhook_id = int(match.group("id"))
            if webhook := self.link_cache.get(webhook_id):
                pass
            else:
                webhook = discord.Webhook.from_url(
                    match.group(0), adapter=discord.AsyncWebhookAdapter(self.session)
                )
                self.link_cache[webhook.id] = webhook
            return webhook

    async def webhook_link_send(
        self,
        link: Union[discord.Webhook, int, str],
        content: str = None,
        *,
        allowed_mentions: discord.AllowedMentions = None,
        **kwargs,
    ) -> Optional[discord.Message]:
        webhook = self.get_webhook_from_link(link)
        if not webhook:
            raise InvalidWebhook("Webhook not cached or found.")

        if allowed_mentions is None:
            allowed_mentions = self.bot.allowed_mentions
        try:
            return await webhook.send(
                content,
                allowed_mentions=allowed_mentions,
                **kwargs,
            )
        except (discord.InvalidArgument, discord.NotFound) as exc:
            try:
                del self.link_cache[webhook.id]
            except KeyError:
                pass
            raise InvalidWebhook("You need to provide a valid webhook link.") from exc

    async def get_webhook(
        self,
        *,
        channel: discord.TextChannel = None,
        me: discord.Member = None,
        author: discord.Member = None,
        reason: str = None,
        ctx: commands.Context = None,
    ) -> discord.Webhook:
        if ctx:
            channel = channel or ctx.channel
            me = me or ctx.me
            author = author or ctx.author
            reason = (reason or f"For the {ctx.command.qualified_name} command",)

        if webhook := self.channel_cache.get(channel.id):
            return webhook
        if me and not channel.permissions_for(me).manage_webhooks:
            raise discord.Forbidden(
                FakeResponse(),
                f"I need permissions to `manage_webhooks` in #{channel}.",
            )
        chan_hooks = await channel.webhooks()
        webhook_list = [w for w in chan_hooks if w.type == discord.WebhookType.incoming]
        if webhook_list:
            webhook = webhook_list[0]
        else:
            creation_reason = (
                f"Webhook creation requested by {author} ({author.id})" if author else ""
            )
            if reason:
                creation_reason += f" Reason: {reason}"
            if len(chan_hooks) == 10:
                await chan_hooks[-1].delete()
            webhook = await channel.create_webhook(
                name=f"{me.name} Webhook",
                reason=creation_reason,
                avatar=await me.avatar_url.read(),
            )
        self.channel_cache[channel.id] = webhook
        return webhook

    async def send_to_channel(
        self,
        channel: discord.TextChannel,
        me: discord.Member = None,
        author: discord.Member = None,
        *,
        reason: str = None,
        ctx: commands.Context = None,
        allowed_mentions: discord.AllowedMentions = None,
        **kwargs,
    ) -> Optional[discord.WebhookMessage]:
        """
        Cog function that other cogs can implement using `bot.get_cog("Webhook")`
        for ease of use when using webhooks and quicker invokes with caching.
        """
        if allowed_mentions is None:
            allowed_mentions = self.bot.allowed_mentions
        tries = 0
        while tries < 5:
            webhook = await self.get_webhook(
                channel=channel, me=me, author=author, reason=reason, ctx=ctx
            )
            try:
                return await webhook.send(allowed_mentions=allowed_mentions, **kwargs)
            except (discord.InvalidArgument, discord.NotFound):
                tries += 1
                del self.channel_cache[channel.id]
