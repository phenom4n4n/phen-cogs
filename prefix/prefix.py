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

import re

import discord
from redbot.core import Config, checks, commands


class Prefix(commands.Cog):
    """Prefix management."""

    def __init__(self, bot):
        self.bot = bot
        self.MENTION_RE = None

    async def red_delete_data_for_user(self, **kwargs):
        return

    @property
    def mention_re(self):
        if not self.MENTION_RE:
            self.MENTION_RE = re.compile(rf"<@!?{self.bot.user.id}>")
        return self.MENTION_RE

    @checks.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.group()
    async def prefix(self, ctx):
        """Prefix management."""

        if not ctx.subcommand_passed:
            embed = await self.gen_prefixes(ctx)
            await ctx.send(embed=embed)

    @checks.admin_or_permissions(manage_guild=True)
    @prefix.command(name="set")
    async def set_prefix(self, ctx, *, prefix: str):
        """Set the prefix for this server."""

        await self.bot.set_prefixes(guild=ctx.guild, prefixes=[prefix])
        embed = await self.gen_prefixes(ctx)
        await ctx.send("Prefix set.", embed=embed)

    @checks.admin_or_permissions(manage_guild=True)
    @prefix.command(name="add")
    async def add_prefix(self, ctx, *, prefix: str):
        """Add a prefix for this server."""

        prefixes = await self.bot.get_valid_prefixes(ctx.guild)
        if prefix in prefixes:
            return await ctx.send("That is already a prefix.")

        if self.bot._cli_flags.mentionable:
            prefixes = [p for p in prefixes if not self.mention_re.match(p)]
        prefixes.append(prefix)
        await ctx.bot.set_prefixes(guild=ctx.guild, prefixes=prefixes)
        embed = await self.gen_prefixes(ctx)
        await ctx.send("Prefix added.", embed=embed)

    @checks.admin_or_permissions(manage_guild=True)
    @prefix.command(name="remove")
    async def remove_prefix(self, ctx, *, prefix: str):
        """Remove a prefix for this server."""

        prefixes = await self.bot.get_valid_prefixes(ctx.guild)
        if prefix not in prefixes:
            return await ctx.send("That is not a valid prefix.")
        if len(prefixes) == 1:
            return await ctx.send("If you removed that prefix, you would have none left.")

        if self.bot._cli_flags.mentionable:
            prefixes = [p for p in prefixes if not self.mention_re.match(p)]
        index = prefixes.index(prefix)
        prefixes.pop(index)
        await self.bot.set_prefixes(guild=ctx.guild, prefixes=prefixes)
        embed = await self.gen_prefixes(ctx)
        await ctx.send("Prefix removed.", embed=embed)

    @checks.admin_or_permissions(manage_guild=True)
    @prefix.command(name="clear", aliases=["reset"])
    async def reset_prefixes(self, ctx):
        """Reset the prefixes for this server."""

        await self.bot.set_prefixes(guild=ctx.guild, prefixes=[])
        embed = await self.gen_prefixes(ctx)
        await ctx.send(f"Reset this server's prefixes.", embed=embed)

    async def gen_prefixes(self, ctx: commands.Context):
        prefixes = []
        for p in await self.bot.get_valid_prefixes(ctx.guild):
            if bot._cli_flags.mentionable and self.mention_re.match(p):
                p.replace("!", "")
                if p in prefixes:
                    continue
            prefixes.append(p)

        prefix_list = "\n".join(f"{index}. {prefix}" for index, prefix in enumerate(prefixes, 1))

        color = await ctx.embed_color()
        return discord.Embed(color=color, title="Prefixes:", description=prefix_list)
