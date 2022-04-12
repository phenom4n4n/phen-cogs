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

import re

import discord
from redbot.core import commands

link_regex = re.compile(
    r"https?:\/\/(?:(?:ptb|canary)\.)?discord(?:app)?\.com"
    r"\/channels\/(?P<guild_id>[0-9]{15,19})\/(?P<channel_id>"
    r"[0-9]{15,19})\/(?P<message_id>[0-9]{15,19})\/?"
)


class LinkToMessage(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Message:
        match = re.search(link_regex, argument)
        if not match:
            raise commands.MessageNotFound(argument)

        guild_id = int(
            match.group("guild_id")
        )  # note: links can have "@me" here but the regex doesn't match that
        channel_id = int(match.group("channel_id"))
        message_id = int(match.group("message_id"))

        message = ctx.bot._connection._get_message(message_id)
        if message:
            return await self.validate_message(ctx, message)

        guild = ctx.bot.get_guild(guild_id)
        if not guild:
            raise commands.GuildNotFound(guild_id)

        channel = guild.get_channel(channel_id)
        if not channel:
            raise commands.ChannelNotFound(channel_id)

        my_perms = channel.permissions_for(guild.me)
        if not my_perms.read_messages:
            raise commands.BadArgument(f"Can't read messages in {channel.mention}.")
        elif not my_perms.read_message_history:
            raise commands.BadArgument(f"Can't read message history in {channel.mention}.")

        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            raise commands.MessageNotFound(argument)
        except discord.Forbidden:
            raise commands.BadArgument(f"Can't read messages in {channel.mention}.")
        else:
            return await self.validate_message(ctx, message)

    async def validate_message(
        self, ctx: commands.Context, message: discord.Message
    ) -> discord.Message:
        if not message.guild:
            raise commands.BadArgument("I can only quote messages from servers.")
        guild = message.guild
        if message.channel.nsfw and not ctx.channel.nsfw:
            raise commands.BadArgument(
                "Messages from NSFW channels cannot be quoted in non-NSFW channels."
            )

        cog = ctx.bot.get_cog("LinkQuoter")
        data = await cog.config.guild(ctx.guild).all()

        if guild.id != ctx.guild.id:
            guild_data = await cog.config.guild(guild).all()
            if not data["cross_server"]:
                raise commands.BadArgument(
                    f"This server is not opted in to quote messages from other servers."
                )
            elif not guild_data["cross_server"]:
                raise commands.BadArgument(
                    f"That server is not opted in to allow its messages to be quoted in other servers."
                )

        member = guild.get_member(ctx.author.id)
        if member:
            author_perms = message.channel.permissions_for(member)
            if not (author_perms.read_message_history and author_perms.read_messages):
                raise commands.BadArgument(
                    f"You don't have permission to read messages in that channel."
                )
        return message
