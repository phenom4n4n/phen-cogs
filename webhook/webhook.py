import asyncio

import aiohttp
import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, close_menu, menu, start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate


async def delete_quietly(ctx: commands.Context):
    if ctx.channel.permissions_for(ctx.me).manage_messages:
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass


class FakeResponse:
    def __init__(self):
        self.status = 403
        self.reason = "Forbidden"


class InvalidWebhook(Exception):
    pass


class Webhook(commands.Cog):
    """Webhook utility commands."""

    __author__ = "PhenoM4n4n"

    def __init__(self, bot):
        self.bot = bot
        self.cache = {}
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def red_delete_data_for_user(self, **kwargs):
        return

    @commands.guild_only()
    @commands.group()
    async def webhook(self, ctx):
        """Webhook related commands."""

    @checks.bot_has_permissions(manage_webhooks=True)
    @checks.admin_or_permissions(manage_webhooks=True)
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

    @checks.admin_or_permissions(manage_webhooks=True)
    @webhook.command()
    async def send(self, ctx: commands.Context, webhook_link: str, *, message: str):
        """Sends a message to the specified webhook using your avatar and display name."""
        await delete_quietly(ctx)
        try:
            await self.webhook_link_send(
                webhook_link, ctx.author.display_name, ctx.author.avatar_url, content=message
            )
        except InvalidWebhook:
            await ctx.send("You need to provide a valid webhook link.")

    @checks.bot_has_permissions(manage_webhooks=True)
    @webhook.command()
    async def say(self, ctx: commands.Context, *, message: str):
        """Sends a message to the channel as a webhook with your avatar and display name."""
        await delete_quietly(ctx)
        await self.send_to_channel(
            ctx.channel,
            ctx.me,
            ctx.author,
            ctx=ctx,
            content=message,
            avatar_url=ctx.author.avatar_url,
            username=ctx.author.display_name,
        )

    @checks.admin_or_permissions(manage_webhooks=True)
    @checks.bot_has_permissions(manage_webhooks=True)
    @webhook.command()
    async def sudo(self, ctx: commands.Context, member: discord.Member, *, message: str):
        """Sends a message to the channel as a webhook with the specified member's avatar and display name."""
        await delete_quietly(ctx)
        await self.send_to_channel(
            ctx.channel,
            ctx.me,
            ctx.author,
            ctx=ctx,
            content=message,
            avatar_url=member.avatar_url,
            username=member.display_name,
        )

    @checks.admin_or_permissions(manage_webhooks=True, manage_guild=True)
    @checks.bot_has_permissions(manage_webhooks=True)
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

    @checks.admin_or_permissions(manage_webhooks=True, manage_guild=True)
    @checks.bot_has_permissions(manage_webhooks=True)
    @webhook.command(hidden=True)
    async def clyde(self, ctx: commands.Context, *, message: str):
        """Sends a message to the channel as a webhook with Clyde's avatar and name."""
        await delete_quietly(ctx)
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
    @checks.has_permissions(manage_webhooks=True)
    @checks.bot_has_permissions(manage_webhooks=True)
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

        if pred.result is True:
            msg = await ctx.send("Deleting webhooks..")
            count = 0
            async with ctx.typing():
                for webhook in webhooks:
                    try:
                        await webhook.delete(
                            reason=f"Guild Webhook Deletion requested by {ctx.author} ({ctx.author.id})"
                        )
                    except discord.HTTPException:
                        pass
                    else:
                        count += 1
            try:
                await msg.edit(content=f"{count} webhooks deleted.")
            except discord.NotFound:
                await ctx.send(f"{count} webhooks deleted.")
        else:
            await ctx.send("Action cancelled.")

    @checks.mod_or_permissions(ban_members=True)
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
        embeds = []
        strings = "\n".join(strings)
        if len(strings) > 2000:
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
    @checks.admin_or_permissions(manage_webhooks=True)
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
            creation_reason = f"Webhook creation requested by {author} ({author.id})"
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
        me: discord.Member,
        author: discord.Member,
        *,
        reason: str = None,
        ctx: commands.Context = None,
        allowed_mentions: discord.AllowedMentions = discord.AllowedMentions(
            users=False, everyone=False, roles=False
        ),
        **kwargs,
    ):
        """Cog function that other cogs can implement using `bot.get_cog("Webhook")`
        for ease of use when using webhooks and quicker invokes with caching."""
        while True:
            webhook = await self.get_webhook(
                channel=channel, me=me, author=author, reason=reason, ctx=ctx
            )
            try:
                await webhook.send(allowed_mentions=allowed_mentions, **kwargs)
            except (discord.InvalidArgument, discord.NotFound):
                del self.cache[channel.id]
            else:
                return True

    async def edit_webhook_message(self, link: str, message_id: int, json: dict):
        async with self.session.patch(
            f"{link}/messages/{message_id}",
            json=json,
            headers={"Content-Type": "application/json"},
        ) as response:
            response = await response.json()
            return response
