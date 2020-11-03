import asyncio
import random

import discord
from redbot.core import Config, bank, checks, commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, close_menu, menu, start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

from .converters import Curable, FuzzyHuman, Infectable, hundred_int


async def is_infected(ctx):
    userState = await ctx.bot.get_cog("Plague").config.user(ctx.author).gameState()
    return userState == "infected"


async def is_healthy(ctx):
    userState = await ctx.bot.get_cog("Plague").config.user(ctx.author).gameState()
    return userState == "healthy"


async def is_doctor(ctx):
    userRole = await ctx.bot.get_cog("Plague").config.user(ctx.author).gameRole()
    return userRole == "Doctor"


async def not_doctor(ctx):
    userRole = await ctx.bot.get_cog("Plague").config.user(ctx.author).gameRole()
    return userRole != "Doctor"


async def not_plaguebearer(ctx):
    userRole = await ctx.bot.get_cog("Plague").config.user(ctx.author).gameRole()
    return userRole != "Plaguebearer"


class Plague(commands.Cog):
    """A plague game."""

    __version__ = "1.0.2"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=2395486659, force_registration=True)
        default_global = {"plagueName": "Plague", "logChannel": None, "rate": 75}
        default_user = {
            "gameRole": "User",
            "gameState": "healthy",
            "notifications": False,
        }
        self.config.register_global(**default_global)
        self.config.register_user(**default_user)

    async def red_delete_data_for_user(self, *, requester: str, user_id: int):
        await self.config.user_from_id(user_id).clear()

    @commands.check(is_infected)
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.guild_only()
    @commands.command(aliases=["cough"], cooldown_after_parsing=True)
    async def infect(self, ctx, *, member: Infectable):
        """Infect another user. You must be infected to use this command."""
        rate = await self.config.rate()
        chance = random.randint(1, 100)
        if chance <= rate:
            result = await self.infect_user(ctx=ctx, user=member)
            await ctx.send(result)
        else:
            await ctx.send(
                f"Luckily **{member.name}** was wearing a mask so they didn't get infected."
            )

    @commands.check(is_doctor)
    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.guild_only()
    @commands.command(cooldown_after_parsing=True)
    async def cure(self, ctx, *, member: Curable):
        """Cure a user. You must be a Doctor to use this command."""
        result = await self.cure_user(ctx=ctx, user=member)
        await ctx.send(result)

    @checks.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.command("plagueprofile", aliases=["pprofile"])
    async def plagueProfile(self, ctx, *, member: FuzzyHuman = None):
        """Show's your Plague Game profile"""
        member = member or ctx.author
        data = await self.config.user(member).all()
        userRole = data["gameRole"]
        userState = data["gameState"]

        title = f"Plague Profile"
        description = (
            f"Role: {userRole}\nState: {userState}\nNotifications: {data['notifications']}"
        )
        color = await ctx.embed_color()
        if userRole == "Doctor":
            thumbnail = "https://contestimg.wish.com/api/webimage/5b556e7ba225161706d6857a-large.jpg?cache_buster=e79a94ce3e105025c5655d67b3d5e1bd"
        elif userRole == "Plaguebearer":
            thumbnail = "https://vignette.wikia.nocookie.net/warhammer40k/images/c/c2/Plaguebearer1.png/revision/latest/scale-to-width-down/340?cb=20170829232116"
        elif userState == "infected":
            thumbnail = (
                "https://cdn.pixabay.com/photo/2020/04/29/07/54/coronavirus-5107715_960_720.png"
            )
        else:
            thumbnail = "https://static.thenounproject.com/png/2090399-200.png"

        embed = discord.Embed(title=title, colour=color, description=description)
        embed.set_thumbnail(url=thumbnail)
        embed.set_author(name=member, icon_url=member.avatar_url)
        await ctx.send(embed=embed)

    @commands.command()
    async def plaguenotify(self, ctx):
        """Enable/Disable Plague Game notifications."""
        notifications = await self.config.user(ctx.author).notifications()
        if notifications != False:
            await self.config.user(ctx.author).notifications.set(False)
            message = "You will no longer be sent Plague Game notifications."
        else:
            await self.config.user(ctx.author).notifications.set(True)
            message = "You will now be sent Plague Game notifications."

        await ctx.send(message)

    @commands.check(not_doctor)
    @commands.check(is_healthy)
    @bank.cost(10000)
    @commands.command(aliases=["plaguedoc"])
    async def plaguedoctor(self, ctx):
        """Become a doctor for 10,000 currency.

        You must be healthy to study at medical school."""
        currency = await bank.get_currency_name(ctx.guild)
        await self.config.user(ctx.author).gameRole.set("Doctor")
        await self.notify_user(ctx=ctx, user=ctx.author, notificationType="doctor")
        await ctx.send(f"{ctx.author} has spent 10,000 {currency} and become a Doctor.")

    @commands.check(not_plaguebearer)
    @commands.check(is_infected)
    @bank.cost(10000)
    @commands.command()
    async def plaguebearer(self, ctx):
        """Become a plaguebearer for 10,000 currency.

        You must be infected to mutate into a plaguebearer."""
        currency = await bank.get_currency_name(ctx.guild)
        await self.config.user(ctx.author).gameRole.set("Plaguebearer")
        await self.notify_user(ctx=ctx, user=ctx.author, notificationType="plaguebearer")
        await ctx.send(f"{ctx.author} has spent 10,000 {currency} and become a Plaguebearer.")

    @commands.check(not_doctor)
    @commands.check(is_healthy)
    @bank.cost(5000)
    @commands.command()
    async def infectme(self, ctx):
        """Get infected for 5,000 currency.

        Why would you willingly infect yourself?"""
        await ctx.send(await self.infect_user(ctx, ctx.author))

    @commands.check(not_plaguebearer)
    @commands.check(is_infected)
    @bank.cost(5000)
    @commands.command()
    async def treatme(self, ctx):
        """Get cured from the plague for 5,000 currency.

        This is America, so the health care is expensive."""
        await ctx.send(await self.cure_user(ctx, ctx.author))

    @checks.is_owner()
    @commands.group()
    async def plagueset(self, ctx):
        """Settings for the Plague game."""

    @plagueset.command()
    async def name(self, ctx, *, name: str = None):
        """Set's the plague's name. Leave blank to show the current name."""
        plagueName = await self.config.plagueName()
        if not name:
            message = f"The current plague's name is `{plagueName}`."
        else:
            await self.config.plagueName.set(name)
            message = f"Set the current plague's name to `{name}`."
        await ctx.send(message)

    @plagueset.command("infect")
    async def manual_infect(self, ctx, *, user: discord.User):
        """Manually infect a user."""
        result = await self.infect_user(ctx=ctx, user=user)
        await ctx.send(result)

    @plagueset.command("cure")
    async def manual_cure(self, ctx, *, user: discord.User):
        """Manually cure a user."""
        result = await self.cure_user(ctx=ctx, user=user)
        await ctx.send(result)

    @plagueset.group(invoke_without_command=True)
    async def infected(self, ctx):
        """Sends a list of the infected users."""
        user_list = await self.config.all_users()
        infected_list = []
        for user, data in user_list.items():
            user = ctx.bot.get_user(user)
            if user:
                userState = data["gameState"]
                if userState == "infected":
                    infected_list.append(f"{user.mention} - {user}")
        if infected_list:
            infected_list = "\n".join(infected_list)
            color = await ctx.embed_color()
            if len(infected_list) > 2000:
                embeds = []
                infected_pages = list(pagify(infected_list))
                for index, page in enumerate(infected_pages, start=1):
                    embed = discord.Embed(color=color, title="Infected Users", description=page)
                    embed.set_footer(text=f"{index}/{len(infected_pages)}")
                    embeds.append(embed)
                await menu(ctx, embeds, DEFAULT_CONTROLS)
            else:
                await ctx.send(
                    embed=discord.Embed(
                        color=color,
                        title="Infected Users",
                        description=infected_list,
                    )
                )
        else:
            await ctx.send("No one has been infected yet..")

    @infected.command(name="guild")
    async def guild_infected(self, ctx, *, guild: discord.Guild = None):
        """Sends a list of the infected users in a guild."""
        if not guild:
            guild = ctx.guild
        user_list = await self.config.all_users()
        infected_list = []
        for user, data in user_list.items():
            user = guild.get_member(user)
            if user:
                userState = data["gameState"]
                if userState == "infected":
                    infected_list.append(f"{user.mention} - {user}")
        if infected_list:
            infected_list = "\n".join(infected_list)
            color = await ctx.embed_color()
            if len(infected_list) > 2000:
                embeds = []
                infected_pages = list(pagify(infected_list))
                for index, page in enumerate(infected_pages, start=1):
                    embed = discord.Embed(color=color, title="Infected Members", description=page)
                    embed.set_footer(text=f"{index}/{len(infected_pages)}")
                    embeds.append(embed)
                await menu(ctx, embeds, DEFAULT_CONTROLS)
            else:
                await ctx.send(
                    embed=discord.Embed(
                        color=color,
                        title="Infected Members",
                        description=infected_list,
                    )
                )
        else:
            await ctx.send("No one has been infected yet..")

    @plagueset.command()
    async def healthy(self, ctx):
        """Sends a list of the healthy users."""
        user_list = await self.config.all_users()
        healthy_list = []
        for user, data in user_list.items():
            user = ctx.bot.get_user(user)
            if user:
                userState = data["gameState"]
                if userState == "healthy":
                    healthy_list.append(f"{user.mention} - {user}")
        if healthy_list:
            healthy_list = "\n".join(healthy_list)
            color = await ctx.embed_color()
            if len(healthy_list) > 2000:
                embeds = []
                healthy_pages = list(pagify(healthy_list))
                for index, page in enumerate(healthy_pages, start=1):
                    embed = discord.Embed(color=color, title="Healthy Users", description=page)
                    embed.set_footer(text=f"{index}/{len(healthy_pages)}")
                    embeds.append(embed)
                await menu(ctx, embeds, DEFAULT_CONTROLS)
            else:
                await ctx.send(
                    embed=discord.Embed(
                        color=color,
                        title="Healthy Users",
                        description=healthy_list,
                    )
                )
        else:
            await ctx.send("No one stored is healthy..")

    @plagueset.command("doctor")
    async def set_doctor(self, ctx, user: discord.User):
        """Set a doctor."""
        await self.config.user(user).gameRole.set("Doctor")
        await self.config.user(user).gameState.set("healthy")
        await self.notify_user(ctx=ctx, user=user, notificationType="doctor")
        await ctx.tick()

    @plagueset.command("plaguebearer")
    async def set_plaguebearer(self, ctx, user: discord.User):
        """Set a plaguebearer."""
        await self.config.user(user).gameRole.set("Plaguebearer")
        await self.config.user(user).gameState.set("infected")
        await self.notify_user(ctx=ctx, user=user, notificationType="plaguebearer")
        await ctx.tick()

    @plagueset.command("channel")
    async def log_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the log channel"""
        if not channel:
            channel = ctx.channel
        await self.config.logChannel.set(channel.id)
        await ctx.send(f"Set {channel.mention} as the log channel.")

    @plagueset.command()
    async def reset(self, ctx):
        """Reset the entire Plague Game."""
        msg = await ctx.send(f"Are you sure you want to reset the current Plague Game?")
        start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
        pred = ReactionPredicate.yes_or_no(msg, ctx.author)
        try:
            await self.bot.wait_for("reaction_add", check=pred, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send("Action cancelled.")
        else:
            if pred.result is True:
                await self.config.clear_all()
                await ctx.send("All data reset.")
            else:
                await ctx.send("Action cancelled.")

    @plagueset.command()
    async def reset_user(self, ctx, user: discord.User):
        """Reset a user."""
        await self.config.user(user).clear()
        try:
            await user.send(f"Your Plague Game data was reset by {ctx.author}.")
        except discord.Forbidden:
            pass
        await ctx.send(f"**{user}** has been reset.")

    @plagueset.command()
    async def rate(self, ctx: commands.Context, rate: hundred_int):
        """Set the Plague Game infection rate."""
        await self.config.rate.set(rate)
        await ctx.send(f"The Plague Game rate has been set to {rate}%.")

    @plagueset.command()
    async def showsettings(self, ctx: commands.Context):
        """View the Plague Game settings."""
        data = await self.config.all()
        channel = self.bot.get_channel(data["logChannel"])
        channel = channel.mention if channel else "None"
        description = (
            f"Name: {data['plagueName']}\n"
            f"Log Channel: {channel}\n"
            f"Infection Rate: {data['rate']}%"
        )
        e = discord.Embed(
            color=await ctx.embed_color(),
            description=description,
        )
        e.set_author(name=f"Plague Game Settings", icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=e)

    async def infect_user(self, ctx, user: discord.User, auto=False):
        game_data = await self.config.all()
        plagueName = game_data["plagueName"]

        channel = game_data["logChannel"]
        channel = ctx.bot.get_channel(channel)
        autoInfect = f" since **{ctx.author}** didn't wear a mask" if auto else ""

        await self.config.user(user).gameState.set("infected")
        await self.notify_user(ctx=ctx, user=user, notificationType="infect")
        if channel:
            await channel.send(
                f"💀| **{user}** on `{ctx.guild}` was just infected with {plagueName} by **{ctx.author}**{autoInfect}."
            )
        return f"**{user.name}** has been infected with {plagueName}{autoInfect}."

    async def cure_user(self, ctx, user: discord.User):
        game_data = await self.config.all()
        plagueName = game_data["plagueName"]
        channel = game_data["logChannel"]
        channel = ctx.bot.get_channel(channel)

        await self.config.user(user).gameState.set("healthy")
        await self.notify_user(ctx=ctx, user=user, notificationType="cure")
        if channel:
            await channel.send(
                f"✨| **{user}** on `{ctx.guild}` was just cured from {plagueName} by **{ctx.author}**."
            )
        return f"**{user.name}** has been cured from {plagueName}."

    async def notify_user(self, ctx, user: discord.User, notificationType: str):
        if not await self.config.user(user).notifications():
            return
        prefixes = await ctx.bot.get_valid_prefixes(ctx.guild)

        plagueName = await self.config.plagueName()
        if notificationType == "infect":
            title = f"You have been infected with {plagueName}!"
            description = (
                f"{ctx.author} infected you. You now have access to `{prefixes[-1]}infect`."
            )
        if notificationType == "cure":
            title = f"You have been cured from {plagueName}!"
            description = f"{ctx.author} cured you."
        if notificationType == "doctor":
            title = f"You are now a Doctor!"
            description = f"{ctx.author} has set you as a Doctor. You now have access to `{prefixes[-1]}cure`."
        if notificationType == "plaguebearer":
            title = f"You are now a Plaguebearer!"
            description = f"{ctx.author} has set you as a Plaguebearer. You now have access to `{prefixes[-1]}infect`."

        embed = discord.Embed(title=title, description=description)
        embed.set_footer(text=f"Use `{prefixes[-1]}plaguenotify` to disable these notifications.")
        try:
            await user.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_command(self, ctx):
        if not ctx.guild or ctx.cog == self or not ctx.message.mentions:
            return
        if await self.bot.cog_disabled_in_guild(self, ctx.guild):
            return
        number = random.randint(1, 10)
        if number > 3:
            return
        perp = await self.config.user(ctx.author).all()
        state = perp["gameState"]
        if state != "infected":
            return

        not_bots = [user for user in ctx.message.mentions if not user.bot]
        infectables = []
        for user in not_bots:
            victim_data = await self.config.user(user).all()
            if (victim_data["gameState"] != "infected") and (victim_data["gameRole"] != "Doctor"):
                infectables.append(user)
        if not infectables:
            return
        victim = random.choice(infectables)
        result = await self.infect_user(ctx, victim, True)
        await ctx.send(result)
