from typing import List

import discord
from redbot.core import commands
from redbot.cogs.alias.alias import Alias
import TagScriptEngine as tse

from .objects import Tag, SilentContext
from .errors import *


class Processor:
    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot:
            return

        try:
            prefix = await Alias.get_prefix(self, message)
        except ValueError:
            return
        tag_command = message.content[len(prefix) :]
        tag_split = tag_command.split(" ", 1)
        if self.get_tag(
            message.guild, tag_split[0], check_global=True
        ) and await self.message_eligible_as_tag(message):
            await self.invoke_tag_message(message, prefix, tag_command)

    async def message_eligible_as_tag(self, message: discord.Message) -> bool:
        if message.guild:
            return isinstance(
                message.author, discord.Member
            ) and await self.bot.message_eligible_as_command(message)
        else:
            return await self.bot.allowed_by_whitelist_blacklist(message.author)

    async def invoke_tag_message(self, message: discord.Message, prefix: str, tag_command: str):
        new_message = copy(message)
        new_message.content = f"{prefix}invoketag False {tag_command}"
        ctx = await self.bot.get_context(new_message)
        await self.bot.invoke(ctx)

    @staticmethod
    def get_seed_from_context(ctx: commands.Context) -> Dict[str, tse.Adapter]:
        author = tse.MemberAdapter(ctx.author)
        target = tse.MemberAdapter(ctx.message.mentions[0]) if ctx.message.mentions else author
        channel = tse.ChannelAdapter(ctx.channel)
        seed = {
            "author": author,
            "user": author,
            "target": target,
            "member": target,
            "channel": channel,
        }
        if ctx.guild:
            guild = tse.GuildAdapter(ctx.guild)
            seed.update(guild=guild, server=guild)
        return seed

    async def process_tag(
        self, ctx: commands.Context, tag: Tag, *, seed_variables: dict = {}, **kwargs
    ) -> str:
        seed = self.get_seed_from_context(ctx)
        seed_variables.update(seed)

        output = tag.run(self.engine, seed_variables=seed_variables, **kwargs)
        await tag.update_config()
        to_gather = []
        command_messages = []
        content = output.body[:2000] if output.body else None
        actions = output.actions
        replying = False

        if actions:
            try:
                await self.validate_checks(ctx, actions)
            except RequireCheckFailure as error:
                response = error.response
                if response is not None:
                    if response.strip():
                        await ctx.send(response[:2000])
                else:
                    start_adding_reactions(ctx.message, ["❌"])
                return

            if delete := actions.get("delete", False):
                to_gather.append(self.delete_quietly(ctx))

            if delete is False and (reactu := actions.get("reactu")):
                to_gather.append(self.react_to_list(ctx.message, reactu))

            if actions.get("commands"):
                for command in actions["commands"]:
                    if command.startswith("tag") or command == "invoketag":
                        await ctx.send("Tag looping isn't allowed.")
                        return
                    new = copy(ctx.message)
                    new.content = ctx.prefix + command
                    command_messages.append(new)

        # this is going to become an asynchronous swamp
        msg = await self.send_tag_response(ctx, actions, content, embed=embed)
        if msg and (react := actions.get("react")):
            to_gather.append(self.react_to_list(ctx, msg, react))
        if command_messages:
            silent = actions.get("silent", False)
            overrides = actions.get("overrides")
            to_gather.append(self.process_commands(command_messages, silent, overrides))

        if to_gather:
            await asyncio.gather(*to_gather)

    @staticmethod
    async def send_quietly(destination: discord.abc.Messageable, content: str = None, **kwargs):
        try:
            return await destination.send(content, **kwargs)
        except discord.HTTPException:
            pass

    async def send_tag_response(
        self,
        ctx: commands.Context,
        actions: dict,
        content: str = None,
        **kwargs,
    ) -> Optional[discord.Message]:
        destination = ctx.channel
        embed = actions.get("embed")
        replying = False

        if target := actions.get("target"):
            if target == "dm":
                destination = await ctx.author.create_dm()
            elif target == "reply":
                replying = True
            else:
                try:
                    chan = await self.channel_converter.convert(ctx, target)
                except commands.BadArgument:
                    pass
                else:
                    if chan.permissions_for(ctx.me).send_messages:
                        destination = chan

        if not (content or embed is not None):
            return
        kwargs["embed"] = embed

        if replying:
            try:
                return await ctx.reply(content, **kwargs)
            except discord.HTTPException:
                return await send_quietly(destination, content, **kwargs)
        else:
            return await send_quietly(destination, content, **kwargs)

    async def process_commands(
        self, messages: List[discord.Message], silent: bool, overrides: dict
    ):
        command_tasks = []
        for message in messages:
            command_task = asyncio.create_task(self.process_command(message, silent, overrides))
            command_tasks.append(command_task)
            await asyncio.sleep(0.1)
        await asyncio.gather(*command_tasks)

    async def process_command(
        self, command_message: discord.Message, silent: bool, overrides: dict
    ):
        ctx = await self.bot.get_context(
            command_message, cls=SilentContext if silent else commands.Context
        )

        if ctx.valid:
            if overrides:
                command = copy(ctx.command)
                # command = commands.Command()
                # command = ctx.command.copy() # does not work as it makes ctx a regular argument
                requires: Requires = copy(command.requires)
                priv_level = requires.privilege_level
                if priv_level not in (
                    PrivilegeLevel.NONE,
                    PrivilegeLevel.BOT_OWNER,
                    PrivilegeLevel.GUILD_OWNER,
                ):
                    if overrides["admin"] and priv_level is PrivilegeLevel.ADMIN:
                        requires.privilege_level = PrivilegeLevel.NONE
                    elif overrides["mod"] and priv_level is PrivilegeLevel.MOD:
                        requires.privilege_level = PrivilegeLevel.NONE
                if overrides["permissions"] and requires.user_perms:
                    requires.user_perms = discord.Permissions.none()
                command.requires = requires
                ctx.command = command
            await self.bot.invoke(ctx)

    async def validate_checks(self, ctx: commands.Context, actions: dict):
        to_gather = []
        if requires := actions.get("requires"):
            to_gather.append(self.validate_requires(ctx, requires))
        if blacklist := actions.get("blacklist"):
            to_gather.append(self.validate_blacklist(ctx, blacklist))
        if to_gather:
            await asyncio.gather(*to_gather)

    async def validate_requires(self, ctx: commands.Context, requires: dict):
        for argument in requires["items"]:
            role_or_channel = await self.role_or_channel_convert(ctx, argument)
            if not role_or_channel:
                continue
            if (
                isinstance(role_or_channel, discord.Role)
                and role_or_channel in ctx.author.roles
                or not isinstance(role_or_channel, discord.Role)
                and role_or_channel == ctx.channel
            ):
                return
        raise RequireCheckFailure(requires["response"])

    async def validate_blacklist(self, ctx: commands.Context, blacklist: dict):
        for argument in blacklist["items"]:
            role_or_channel = await self.role_or_channel_convert(ctx, argument)
            if not role_or_channel:
                continue
            if (
                isinstance(role_or_channel, discord.Role)
                and role_or_channel in ctx.author.roles
                or not isinstance(role_or_channel, discord.Role)
                and role_or_channel == ctx.channel
            ):
                raise RequireCheckFailure(blacklist["response"])

    async def role_or_channel_convert(self, ctx: commands.Context, argument: str):
        objects = await asyncio.gather(
            self.role_converter.convert(ctx, argument),
            self.channel_converter.convert(ctx, argument),
            return_exceptions=True,
        )
        objects = [obj for obj in objects if isinstance(obj, (discord.Role, discord.TextChannel))]
        return objects[0] if objects else None

    @staticmethod
    async def react_to_list(ctx: commands.Context, message: discord.Message, args: List[str]):
        if not (message and args):
            return
        for arg in args:
            try:
                arg = await self.emoji_converter.convert(ctx, arg)
            except commands.BadArgument:
                pass
            try:
                await ctx.message.add_reaction(arg)
            except discord.HTTPException:
                pass

    @staticmethod
    async def delete_quietly(ctx: commands.Context):
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass
