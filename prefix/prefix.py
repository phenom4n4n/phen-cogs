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
from typing import List

import discord
from redbot.core import Config, commands


class Prefix(commands.Cog):
    """Prefix management."""

    def __init__(self, bot):
        self.bot = bot
        self.MENTION_RE = None

    async def red_delete_data_for_user(self, **kwargs):
        return

    @property
    def mentionable(self) -> bool:
        return self.bot._cli_flags.mentionable

    @property
    def mention_re(self) -> re.Pattern:
        if not self.MENTION_RE:
            self.MENTION_RE = re.compile(rf"^<@!?{self.bot.user.id}>$")
        return self.MENTION_RE

    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    async def prefix(self, ctx: commands.Context):
        """
        Manage server prefixes.

        Running this command without subcommands will show this server's prefixes.

        **Example:**
        `[p]prefix`
        """
        embed = await self.prefix_embed(ctx)
        await ctx.send(embed=embed)

    @commands.admin_or_permissions(manage_guild=True)
    @prefix.command(name="set", aliases=["="], require_var_positional=True)
    async def prefix_set(self, ctx: commands.Context, *prefixes: str):
        """
        Set the prefixes for this server.

        Multiple prefixes can be set at once.
        To add a prefix with spaces, use quotes.
        This will overwrite any current prefixes.

        **Examples:**
        `[p]prefix set ! n!`
        `[p]prefix set .. & "Hey siri, "`
        """
        await self.bot.set_prefixes(guild=ctx.guild, prefixes=prefixes)
        embed = await self.prefix_embed(ctx)
        es = "es" if len(prefixes) > 1 else ""
        await ctx.send(f"Prefix{es} set.", embed=embed)

    @commands.admin_or_permissions(manage_guild=True)
    @prefix.command(name="add", aliases=["+"])
    async def prefix_add(self, ctx: commands.Context, prefix: str):
        """
        Add a prefix to this server's prefix list.

        Use quotes to add a prefix with spaces.

        **Examples:**
        `[p]prefix add ?`
        `[p]prefix + "[botname], can you please "`
        """
        prefixes = await self.get_prefixes(ctx.guild)
        if prefix in prefixes:
            return await ctx.send("That is already a prefix.")

        prefixes.append(prefix)
        await self.bot.set_prefixes(guild=ctx.guild, prefixes=prefixes)
        embed = await self.prefix_embed(ctx)
        await ctx.send("Prefix added.", embed=embed)

    @commands.admin_or_permissions(manage_guild=True)
    @prefix.command(name="remove", aliases=["-"])
    async def prefix_remove(self, ctx: commands.Context, prefix: str):
        """
        Remove a prefix from this server's prefix list.

        Use quotes to remove a prefix with spaces.

        **Examples:**
        `[p]prefix remove ~`
        `[p]prefix - "Alexa, "`
        """
        prefixes = await self.get_prefixes(ctx.guild)
        if prefix not in prefixes:
            return await ctx.send("That is not a valid prefix.")
        if len(prefixes) == 1:
            return await ctx.send("If you removed that prefix, you would have none left.")

        prefixes.remove(prefix)
        await self.bot.set_prefixes(guild=ctx.guild, prefixes=prefixes)
        embed = await self.prefix_embed(ctx)
        await ctx.send("Prefix removed.", embed=embed)

    @commands.admin_or_permissions(manage_guild=True)
    @prefix.command(name="clear", aliases=["reset"])
    async def prefix_clear(self, ctx: commands.Context):
        """
        Reset this server's prefixes to the default list.

        This cannot be undone.

        **Example:**
        `[p]prefix clear`
        """
        await self.bot.set_prefixes(guild=ctx.guild, prefixes=[])
        embed = await self.prefix_embed(ctx)
        await ctx.send(f"Reset this server's prefixes.", embed=embed)

    async def get_prefixes(self, guild: discord.Guild) -> List[str]:
        prefixes = await self.bot.get_valid_prefixes(guild)
        if self.mentionable:
            prefixes = [p for p in prefixes if not self.mention_re.match(p)]
        return prefixes

    async def prefix_embed(self, ctx: commands.Context) -> discord.Embed:
        prefixes = []
        for p in await self.bot.get_valid_prefixes(ctx.guild):
            if self.mentionable and self.mention_re.match(p):
                p = p.replace("!", "")
                if p in prefixes:
                    continue
            prefixes.append(p)

        prefix_list = "\n".join(f"{index}. {prefix}" for index, prefix in enumerate(prefixes, 1))

        color = await ctx.embed_color()
        return discord.Embed(color=color, title="Prefixes:", description=prefix_list)
