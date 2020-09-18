import discord

from redbot.core import Config, checks, commands


class Prefix(commands.Cog):
    """Prefix management."""

    def __init__(self, bot):
        self.bot = bot

    async def red_delete_data_for_user(self, **kwargs):
        return

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

        prefix = [prefix]
        await ctx.bot.set_prefixes(guild=ctx.guild, prefixes=prefix)
        embed = await self.gen_prefixes(ctx)
        await ctx.send("Prefix set.", embed=embed)

    @checks.admin_or_permissions(manage_guild=True)
    @prefix.command(name="add")
    async def add_prefix(self, ctx, *, prefix: str):
        """Add a prefix for this server."""

        prefixes = await self.bot.get_valid_prefixes(ctx.guild)
        if prefix in prefixes:
            return await ctx.send("That is already a prefix.")
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
        index = prefixes.index(prefix)
        prefixes.pop(index)
        await ctx.bot.set_prefixes(guild=ctx.guild, prefixes=prefixes)
        embed = await self.gen_prefixes(ctx)
        await ctx.send("Prefix removed.", embed=embed)

    @checks.admin_or_permissions(manage_guild=True)
    @prefix.command(name="clear", aliases=["reset"])
    async def reset_prefixes(self, ctx):
        """Reset the prefixes for this server."""

        await ctx.bot.set_prefixes(guild=ctx.guild, prefixes=[])
        embed = await self.gen_prefixes(ctx)
        await ctx.send(f"Reset this server's prefixes.", embed=embed)

    async def gen_prefixes(self, ctx: commands.Context):
        prefixes = await self.bot.get_valid_prefixes(ctx.guild)
        count = 0
        prefix_list = "\n".join([f"{index}. {prefix}" for index, prefix in enumerate(prefixes, 1)])
        color = await self.bot.get_embed_color(ctx)
        embed = discord.Embed(color=color, title="Prefixes:", description=prefix_list)
        return embed
