from collections import Counter
from typing import Optional, TypedDict

import discord
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import humanize_list

from .core import Connect4Game
from .views import ConfirmationView, Connect4View


class EmbedFields(TypedDict):
    name: str
    value: str
    inline: Optional[bool]


class Connect4(commands.Cog):
    """
    Play Connect 4!
    """

    EMOJI_MEDALS = {
        1: "\N{FIRST PLACE MEDAL}",
        2: "\N{SECOND PLACE MEDAL}",
        3: "\N{THIRD PLACE MEDAL}",
    }

    __version__ = "1.1.0"

    __authors__ = ["Benjamin Mintz", "flare", "PhenoM4n4n"]

    def __init__(self, bot):
        self.bot = bot
        defaults = {"stats": {"played": 0, "ties": 0, "wins": {}, "losses": {}, "draws": {}}}
        self.config = Config.get_conf(self, identifier=4268355870, force_registration=True)
        self.config.register_guild(**defaults)

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        formatted = [
            f"{pre_processed}{n}",
            f"Cog Version: **{self.__version__}**",
            f"Authors: {humanize_list(self.__authors__)}",
        ]
        return "\n".join(formatted)

    @staticmethod
    async def start_game(ctx: commands.Context, user: discord.Member) -> bool:
        """
        Whether to start the connect 4 game.
        """
        msg = (
            f"{user.mention}, {ctx.author.name} is challenging you to a game of Connect4. "
            "Press the buttons to accept or deny their challenge."
        )
        return await ConfirmationView.confirm(ctx, msg, user_id=user.id)

    @commands.group(invoke_without_command=True)
    async def connect4(self, ctx: commands.Context, member: discord.Member):
        """
        Play Connect 4 with another player.
        """
        if member.bot:
            return await ctx.send("That's a bot, silly!")
        if ctx.author == member:
            return await ctx.send("You can't play yourself!")
        if not await self.start_game(ctx, member):
            return

        game = Connect4Game(ctx.author, member)
        view = Connect4View(self, game)
        await view.start(ctx)
        await view.wait()
        await self.store_stats(ctx.guild, game)

    @connect4.command("stats")
    async def connect4_stats(self, ctx: commands.Context, member: discord.Member = None):
        """
        View Connect 4 stats.
        """
        stats = await self.config.guild(ctx.guild).stats()
        if member:
            member_id = str(member.id)
            wins = stats["wins"].get(member_id, 0)
            losses = stats["losses"].get(member_id, 0)
            draws = stats["draws"].get(member_id, 0)
            description = [
                f"Wins: {wins}",
                f"Losses: {losses}",
                f"Draws: {draws}",
            ]
            e = discord.Embed(color=member.color, description="\n".join(description))
            e.set_author(name=f"{member} Connect 4 Stats", icon_url=ctx.author.display_avatar.url)
        else:
            games_played = stats["played"]
            ties = stats["ties"]
            description = [
                f"Games played: {games_played}",
                f"Ties: {ties}",
            ]
            e = discord.Embed(color=await ctx.embed_color(), description="\n".join(description))
            if wins := self.create_field(stats, "wins"):
                e.add_field(**wins)
            if losses := self.create_field(stats, "losses"):
                e.add_field(**losses)
            if draws := self.create_field(stats, "draws"):
                e.add_field(**draws)
            e.set_author(name=f"{ctx.guild} Connect 4 Stats", icon_url=ctx.guild.icon.url)
        await ctx.send(embed=e)

    @staticmethod
    def add_stat(stats: dict, key: str, user_id: str):
        if user_id in stats[key]:
            stats[key][user_id] += 1
        else:
            stats[key][user_id] = 1

    async def store_stats(self, guild: discord.Guild, game: Connect4Game):
        winnernum = game.whomst_won()
        if winnernum in (Connect4Game.FORFEIT, Connect4Game.NO_WINNER):
            return

        player1_id = str(game.player1.id)
        player2_id = str(game.player2.id)
        async with self.config.guild(guild).stats() as stats:
            stats["played"] += 1
            if winnernum == Connect4Game.TIE:
                stats["ties"] += 1
                self.add_stat(stats, "draw", player1_id)
                self.add_stat(stats, "draw", player2_id)
            else:
                winner, loser = (
                    (player1_id, player2_id) if winnernum == 1 else (player2_id, player1_id)
                )
                self.add_stat(stats, "wins", winner)
                self.add_stat(stats, "losses", loser)

    def create_field(self, stats: dict, key: str) -> EmbedFields:
        counter = Counter(stats[key])
        total = sum(counter.values())
        values = []
        for place, (user_id, win_count) in enumerate(counter.most_common(3), 1):
            medal = self.EMOJI_MEDALS[place]
            values.append(f"{medal} <@!{user_id}>: {win_count}")
        return (
            {"name": f"{key.title()}: {total}", "value": "\n".join(values), "inline": True}
            if values
            else {}
        )
