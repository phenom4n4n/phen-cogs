import asyncio
import logging
from copy import copy
from typing import Dict, List, Optional

import discord
import TagScriptEngine as tse
from redbot.core import commands
from redbot.core.utils.menus import start_adding_reactions

from .abc import MixinMeta
from .blocks import DeleteBlock, ReactBlock, SilentBlock
from .errors import BlacklistCheckFailure, RequireCheckFailure, WhitelistCheckFailure
from .objects import SilentContext, Tag

log = logging.getLogger("red.phenom4n4n.tags.processor")


class Processor(MixinMeta):
    def __init__(self):
        self.role_converter = commands.RoleConverter()
        self.channel_converter = commands.TextChannelConverter()
        self.member_converter = commands.MemberConverter()
        self.emoji_converter = commands.EmojiConverter()

        self.bot.add_dev_env_value("tse", lambda ctx: tse)
        super().__init__()

    def cog_unload(self):
        self.bot.remove_dev_env_value("tse")
        super().cog_unload()

    async def initialize_interpreter(self, data: dict = None):
        if not data:
            data = await self.config.all()
        self.dot_parameter = data["dot_parameter"]

        tse_blocks = [
            tse.MathBlock(),
            tse.RandomBlock(),
            tse.RangeBlock(),
            tse.AnyBlock(),
            tse.IfBlock(),
            tse.AllBlock(),
            tse.BreakBlock(),
            tse.StrfBlock(),
            tse.StopBlock(),
            tse.AssignmentBlock(),
            tse.FiftyFiftyBlock(),
            tse.ShortCutRedirectBlock("args"),
            tse.LooseVariableGetterBlock(),
            tse.SubstringBlock(),
            tse.EmbedBlock(),
            tse.ReplaceBlock(),
            tse.PythonBlock(),
            tse.URLEncodeBlock(),
            tse.RequireBlock(),
            tse.BlacklistBlock(),
            tse.CommandBlock(),
            tse.OverrideBlock(),
            tse.RedirectBlock(),
            tse.CooldownBlock(),
        ]
        tag_blocks = [
            DeleteBlock(),
            SilentBlock(),
            ReactBlock(),
        ]
        interpreter = tse.AsyncInterpreter if data["async_enabled"] else tse.Interpreter
        self.async_enabled = data["async_enabled"]
        self.engine = interpreter(tse_blocks + tag_blocks)
        for block in await self.compile_blocks(data):
            self.engine.blocks.append(block())

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError, unhandled_by_cog=False
    ):
        if not isinstance(error, commands.CommandNotFound):
            return
        message: discord.Message = ctx.message
        tag = self.get_tag(ctx.guild, ctx.invoked_with, check_global=True)
        if tag and await self.message_eligible_as_tag(message):
            prefix = ctx.prefix
            tag_command = message.content[len(prefix) :]
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
        self, ctx: commands.Context, tag: Tag, *, seed_variables: dict = None, **kwargs
    ) -> str:
        seed_variables = {} if seed_variables is None else seed_variables
        seed = self.get_seed_from_context(ctx)
        seed_variables.update(seed)

        output = await tag.run(seed_variables, **kwargs)
        await tag.update_config()
        dispatch_prefix = "tag" if tag.guild_id else "g-tag"
        self.bot.dispatch("commandstats_action_v2", f"{dispatch_prefix}:{tag}", ctx.guild)
        to_gather = []
        command_messages = []
        content = output.body[:2000] if output.body else None
        actions = output.actions

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
                to_gather.append(self.react_to_list(ctx, ctx.message, reactu))

            if actions.get("commands"):
                for command in actions["commands"]:
                    if command == "invoketag":
                        await ctx.send("Tag looping isn't allowed.")
                        return
                    new = copy(ctx.message)
                    new.content = ctx.prefix + command
                    command_messages.append(new)

        # this is going to become an asynchronous swamp
        msg = await self.send_tag_response(ctx, actions, content)
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
                destination = ctx.author
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
            ref = ctx.message.to_reference(fail_if_not_exists=False)
            kwargs["reference"] = ref

        return await self.send_quietly(destination, content, **kwargs)

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
        command_cls = SilentContext if silent else commands.Context
        ctx = await self.bot.get_context(command_message, cls=command_cls)
        if not ctx.valid:
            return
        if overrides:
            ctx.command = self.handle_overrides(ctx.command, overrides)
        await self.bot.invoke(ctx)

    @classmethod
    def handle_overrides(cls, command: commands.Command, overrides: dict) -> commands.Command:
        overriden_command = copy(command)
        # overriden_command = command.copy() # does not work as it makes ctx a regular argument
        # overriden_command.cog = command.cog
        requires: commands.Requires = copy(command.requires)
        priv_level = requires.privilege_level
        if priv_level not in (
            commands.PrivilegeLevel.NONE,
            commands.PrivilegeLevel.BOT_OWNER,
            commands.PrivilegeLevel.GUILD_OWNER,
        ):
            if overrides["admin"] and priv_level is commands.PrivilegeLevel.ADMIN:
                requires.privilege_level = commands.PrivilegeLevel.NONE
            elif overrides["mod"] and priv_level is commands.PrivilegeLevel.MOD:
                requires.privilege_level = commands.PrivilegeLevel.NONE

        if overrides["permissions"] and requires.user_perms:
            requires.user_perms = discord.Permissions.none()
        overriden_command.requires = requires

        if all_commands := getattr(overriden_command, "all_commands", None):
            all_commands = all_commands.copy()
            for name, child in all_commands.copy().items():
                all_commands[name] = cls.handle_overrides(child, overrides)
            overridden_command.all_commands = all_commands
        return overriden_command

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
        raise WhitelistCheckFailure(requires["response"])

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
                raise BlacklistCheckFailure(blacklist["response"])

    async def role_or_channel_convert(self, ctx: commands.Context, argument: str):
        objects = await asyncio.gather(
            self.role_converter.convert(ctx, argument),
            self.channel_converter.convert(ctx, argument),
            return_exceptions=True,
        )
        objects = [obj for obj in objects if isinstance(obj, (discord.Role, discord.TextChannel))]
        return objects[0] if objects else None

    async def react_to_list(
        self, ctx: commands.Context, message: discord.Message, args: List[str]
    ):
        if not (message and args):
            return
        for arg in args:
            try:
                arg = await self.emoji_converter.convert(ctx, arg)
            except commands.BadArgument:
                pass
            try:
                await message.add_reaction(arg)
            except discord.HTTPException:
                pass

    @staticmethod
    async def delete_quietly(ctx: commands.Context):
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass
