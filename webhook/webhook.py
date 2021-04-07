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
from typing import Optional

import aiohttp
import discord
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, close_menu, menu, start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate


async def _monkeypatch_send(ctx: commands.Context, content: str = None, **kwargs) -> discord.Message:
    self = ctx.bot.get_cog("Webhook")
    original_kwargs = kwargs.copy()
    try:
        webhook = await self.get_webhook(ctx=ctx)
        kwargs["username"] = ctx.author.display_name
        kwargs["avatar_url"] = ctx.author.avatar_url
        kwargs["wait"] = True
        return await webhook.send(content, **kwargs)
    except discord.HTTPException:
        return await super(commands.Context, ctx).send(content, **original_kwargs)


class FakeResponse:
    def __init__(self):
        self.status = 403
        self.reason = "Forbidden"


class InvalidWebhook(Exception):
    pass


class Webhook(commands.Cog):
    """Webhook utility commands."""

    __author__ = "PhenoM4n4n"

    __version__ = "1.1.2"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=2352346345723453463,
            force_registration=True,
        )
        self.config.register_global(monkey_patch=False)

        self.cache = {}
        self.session = aiohttp.ClientSession()

        self.old_send = commands.Context.send
        self._monkey_patched = False

    async def initialize(self):
        data = await self.config.all()
        if data["monkey_patch"]:
            self._apply_monkeypatch()

    def cog_unload(self):
        self._remove_monkeypatch()
        asyncio.create_task(self.session.close())

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
    async def send(self, ctx: commands.Context, webhook_link: str, *, message: str):
        """Sends a message to the specified webhook using your avatar and display name."""
        await self.delete_quietly(ctx)
        try:
            await self.webhook_link_send(
                webhook_link, ctx.author.display_name, ctx.author.avatar_url, content=message
            )
        except InvalidWebhook:
            await ctx.send("You need to provide a valid webhook link.")

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
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True),
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
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True),
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
    @webhook.command()
    async def perms(self, ctx):
        """Show all members in the server that have `manage_webhook` permissions."""
        await ctx.trigger_typing()
        members = []
        strings = []
        roles = []
        for role in ctx.guild.roles:
            if role.permissions.is_superset(
                discord.Permissions(536870912)
            ) or role.permissions.is_superset(discord.Permissions(8)):
                roles.append(role)
                for member in role.members:
                    if member not in members:
                        members.append(member)
                        string = (
                            f"[{member.mention} - {member}](https://www.youtube.com/watch?v=dQw4w9WgXcQ&ab_channel=RickAstleyVEVO 'This user is a bot')"
                            if member.bot
                            else f"{member.mention} - {member}"
                        )
                        strings.append(string)
        if not members:
            await ctx.send("No one here has `manage_webhook` permissions other than the owner.")
        strings = "\n".join(strings)
        if len(strings) > 2000:
            embeds = []
            for page in pagify(strings):
                embed = discord.Embed(
                    color=await ctx.embed_color(),
                    title="Users with `manage_webhook` Permissions",
                    description=page,
                )
                if roles:
                    embed.add_field(
                        name="Roles:",
                        value=humanize_list([role.mention for role in roles]),
                        inline=False,
                    )
                embeds.append(embed)
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            embed = discord.Embed(
                color=await ctx.embed_color(),
                title="Users with `manage_webhook` Permissions",
                description=strings,
            )
            if roles:
                embed.add_field(
                    name="Roles:",
                    value=humanize_list([role.mention for role in roles]),
                    inline=False,
                )
            emoji = self.bot.get_emoji(736038541364297738) or "❌"
            await menu(ctx, [embed], {emoji: close_menu})

    @commands.max_concurrency(1, commands.BucketType.channel)
    @commands.admin_or_permissions(manage_webhooks=True)
    @webhook.command()
    async def session(self, ctx: commands.Context, webhook_link: str):
        """Initiate a session within this channel sending messages to a specified webhook link."""
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            try:
                await ctx.message.delete()
            except discord.NotFound:
                pass
        e = discord.Embed(
            color=0x49FC95,
            title="Webhook Session Initiated",
            description=f"Session Created by `{ctx.author}`.",
        )
        initial_result = await self.webhook_link_send(
            webhook_link, "Webhook Session", "https://imgur.com/BMeddyn.png", embed=e
        )
        if initial_result is not True:
            return await ctx.send(initial_result)
        await ctx.send(
            "I will send all messages in this channel to the webhook until "
            "the session is closed by saying 'close' or there are 2 minutes of inactivity.",
            embed=e,
        )
        while True:
            try:
                result = await self.bot.wait_for(
                    "message_without_command",
                    check=lambda x: x.channel == ctx.channel and not x.author.bot and x.content,
                    timeout=120,
                )
            except asyncio.TimeoutError:
                return await ctx.send("Session closed.")
            if result.content.lower() == "close":
                return await ctx.send("Session closed.")
            send_result = await self.webhook_link_send(
                webhook_link,
                result.author.display_name,
                result.author.avatar_url,
                content=result.content,
            )
            if send_result is not True:
                return await ctx.send("The webhook was deleted so this session has been closed.")

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

    async def webhook_link_send(
        self,
        link: str,
        username: str,
        avatar_url: str,
        *,
        allowed_mentions: discord.AllowedMentions = discord.AllowedMentions(
            users=False, everyone=False, roles=False
        ),
        **kwargs,
    ):
        try:
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(
                    link, adapter=discord.AsyncWebhookAdapter(session)
                )
                await webhook.send(
                    username=username,
                    avatar_url=avatar_url,
                    allowed_mentions=allowed_mentions,
                    **kwargs,
                )
                return True
        except (discord.InvalidArgument, discord.NotFound):
            raise InvalidWebhook("You need to provide a valid webhook link.")

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

        if webhook := self.cache.get(channel.id):
            return webhook
        if me and not channel.permissions_for(me).manage_webhooks:
            raise discord.Forbidden(
                FakeResponse(),
                f"I need permissions to `manage_webhooks` in #{channel.name}.",
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
        self.cache[channel.id] = webhook
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
                del self.cache[channel.id]

    async def edit_webhook_message(self, link: str, message_id: int, json: dict):
        async with self.session.patch(
            f"{link}/messages/{message_id}",
            json=json,
            headers={"Content-Type": "application/json"},
        ) as response:
            response = await response.json()
            return response
