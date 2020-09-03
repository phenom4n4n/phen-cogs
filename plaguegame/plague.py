import discord
import asyncio

from redbot.core import Config, checks, commands, bank
from redbot.core.utils.menus import menu

class Plague(commands.Cog):
    """A plague game."""

    def __init__(self, bot):
        self.config = Config.get_conf(self, identifier=2395486659)
        default_global = {
            "plagueName": "Plague",
            "logChannel": None
        }
        default_user = {
            "gameRole": "User",
            "gameState": "healthy",
            "notifications": False,
        }
        self.config.register_global(**default_global)
        self.config.register_user(**default_user)

    async def red_delete_data_for_user(self, *, requester: str, user_id: int):
        await self.config.user_from_id(user_id).clear()

    async def is_infected(ctx):
        userState = await ctx.cog.config.user(ctx.author).gameState()
        return userState == "infected"

    async def is_healthy(ctx):
        userState = await ctx.cog.config.user(ctx.author).gameState()
        return userState == "healthy"

    async def is_doctor(ctx):
        userRole = await ctx.cog.config.user(ctx.author).gameRole()
        return userRole == "Doctor"

    @commands.check(is_infected)
    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.guild_only()
    @commands.command(aliases=["cough"])
    async def infect(self, ctx, *, member: discord.Member):
        """Infect another user. You must be infected to use this command."""

        result = await self.infect_user(ctx=ctx, user=member)
        await ctx.send(result)

    @commands.check(is_doctor)
    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.guild_only()
    @commands.command()
    async def cure(self, ctx, *, member: discord.Member):
        """Cure a user. You must be a Doctor to use this command."""
        
        result = await self.cure_user(ctx=ctx, user=member)
        await ctx.send(result)

    @checks.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.command("plagueprofile")
    async def plagueProfile(self, ctx, *, member: discord.Member = None):
        """Show's your Plague Game profile"""
        if not member:
            member = ctx.author
        data = await self.config.user(member).all()
        userRole = data["gameRole"]
        userState = data["gameState"]

        title = f"Plague Profile"
        description = f"Role: {userRole}\nState: {userState}\nNotifications: {data['notifications']}"
        color = await ctx.embed_color()
        if userRole == "Doctor":
            thumbnail = "https://contestimg.wish.com/api/webimage/5b556e7ba225161706d6857a-large.jpg?cache_buster=e79a94ce3e105025c5655d67b3d5e1bd"
        elif userRole == "Plaguebearer":
            thumbnail = "https://vignette.wikia.nocookie.net/warhammer40k/images/c/c2/Plaguebearer1.png/revision/latest/scale-to-width-down/340?cb=20170829232116"
        elif userState == "infected":
            thumbnail = "https://cdn.pixabay.com/photo/2020/04/29/07/54/coronavirus-5107715_960_720.png"
        else:
            thumbnail = "https://static.thenounproject.com/png/2090399-200.png"

        embed = discord.Embed(
            title=title,
            colour=color,
            description=description
            )
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

    @bank.cost(5000)
    @commands.check(is_healthy)
    @commands.command(aliases=["plaguedoc"])
    async def plaguedoctor(self, ctx):
        """Become a doctor for 5,000 currency.
        
        You must not be infected to run this command."""
    
        currency = await bank.get_currency_name(ctx.guild)
        gameRole = await self.config.user(ctx.author).gameRole()
        if gameRole == "Doctor":
            return await ctx.send(f"You are already a Doctor! Why waste another 5,000 {currency} buying it again?")
        await self.config.user(ctx.author).gameRole.set("Doctor")
        await self.notify_user(ctx=ctx, user=ctx.author, notificationType="doctor")
        await ctx.send(f"{ctx.author} has spent 5,000 {currency} and become a Doctor.")

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
        for user in user_list:
            user = ctx.bot.get_user(user)
            if user:
                userState = await self.config.user(user).gameState()
                if userState == "infected":
                    infected_list.append(user.mention)
        embedDescription = "\n".join(infected_list[:93])
        embed = discord.Embed(title="Infected Users", description=embedDescription)
        await ctx.send(embed=embed)

    @infected.command(name="guild")
    async def guild_infected(self, ctx, *, guild: discord.Guild = None):
        """Sends a list of the infected users in a guild."""
        if not guild:
            guild = ctx.guild
        user_list = await self.config.all_users()
        infected_list = []
        for user in user_list:
            user = guild.get_member(user)
            if user:
                userState = await self.config.user(user).gameState()
                if userState == "infected":
                    infected_list.append(user.mention)
        embedDescription = "\n".join(infected_list[:93])
        embed = discord.Embed(title="Infected Users", description=embedDescription)
        await ctx.send(embed=embed)

    @plagueset.command()
    async def healthy(self, ctx):
        """Sends a list of the healthy users."""

        user_list = await self.config.all_users()
        healthy_list = []
        for user in user_list:
            user = ctx.bot.get_user(user)
            if user:
                userState = await self.config.user(user).gameState()
                if userState == "healthy":
                    healthy_list.append(user.mention)
        embedDescription = "\n".join(healthy_list)
        embed = discord.Embed(title="Healthy Users", description=embedDescription)
        await ctx.send(embed=embed)

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
        
        await self.config.clear_all()
        await ctx.tick()

    @plagueset.command()
    async def reset_user(self, ctx, user: discord.User):
        """Reset a user."""

        await self.config.user(user).clear()
        await user.send(f"Your Plague Game data was reset by {ctx.author}.")
        await ctx.send(f"`{user}` has been reset.")

    async def infect_user(self, ctx, *, user: discord.User):
        plagueName = await self.config.plagueName()
        state = await self.config.user(user).gameState()
        role = await self.config.user(user).gameRole()
        if user.bot:
            return "You can't infect bots."
        if state == "infected":
            return f"`{user.name}` is already infected with {plagueName}."
        elif role == "Doctor":
            return f"You cannot infect a Doctor!"
        else:
            channel = await self.config.logChannel()
            channel = ctx.bot.get_channel(channel)

            await self.config.user(user).gameState.set("infected")
            await self.notify_user(ctx= ctx, user=user, notificationType="infect")
            if channel:
                await channel.send(f"💀| Someone on `{ctx.guild}` was just infected with {plagueName}.")
            return f"`{user.name}` has been infected with {plagueName}."

    async def cure_user(self, ctx, *, user: discord.User):
        plagueName = await self.config.plagueName()
        state = await self.config.user(user).gameState()
        role = await self.config.user(user).gameRole()
        if user.bot:
            return "You can't cure bots."
        if state == "healthy":
            return f"`{user.name}` is already healthy."
        elif role == "Plaguebearer":
            return f"You cannot cure a Plaguebearer!"
        else:
            channel = await self.config.logChannel()
            channel = ctx.bot.get_channel(channel)

            await self.config.user(user).gameState.set("healthy")
            await self.notify_user(ctx=ctx, user=user, notificationType="cure")
            if channel:
                await channel.send(f"✨| Someone on `{ctx.guild}` was just cured from {plagueName}.")
            return f"`{user.name}` has been cured from {plagueName}."

    async def notify_user(self, ctx, *, user: discord.User, notificationType: str):
        if not await self.config.user(user).notifications():
            return
        prefixes = await ctx.bot.get_valid_prefixes(ctx.guild)

        plagueName = await self.config.plagueName()
        if notificationType == "infect":
            title = f"You have been infected with {plagueName}!"
            description = f"{ctx.author} infected you. You now have access to `{prefixes[-1]}infect`."
        if notificationType == "cure":
            title = f"You have been cured from {plagueName}!"
            description = f"{ctx.author} cured you."
        if notificationType == "doctor":
            title = f"You are now a Doctor!"
            description = f"{ctx.author} has set you as a Doctor. You now have access to `{prefixes[-1]}cure`."
        if notificationType == "plaguebearer":
            title = f"You are now a Plaguebearer!"
            description = f"{ctx.author} has set you as a Plaguebearer. You now have access to `{prefixes[-1]}infect`."
        embed = discord.Embed(title = title, description = description)
        embed.set_footer(text=f"Use `{prefixes[-1]}plaguenotify` to disable these notifications.")
        try:
            await user.send(embed=embed)
        except discord.errors.Forbidden:
            pass
