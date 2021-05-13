import asyncio
import logging
from copy import copy
from functools import partial
from typing import List, Optional

import discord
import TagScriptEngine as tse
from redbot.core import commands

from .abc import MixinMeta
from .blocks import HideBlock
from .errors import (
    BlacklistCheckFailure,
    MissingTagPermissions,
    RequireCheckFailure,
    WhitelistCheckFailure,
)
from .models import InteractionCommand, SlashOptionType
from .objects import FakeMessage, SlashContext, SlashTag
from .utils import dev_check

PL = commands.PrivilegeLevel
RS = commands.Requires

log = logging.getLogger("red.phenom4n4n.slashtags.processor")


class Processor(MixinMeta):
    OPTION_ADAPTERS = {
        SlashOptionType.STRING: tse.StringAdapter,
        SlashOptionType.INTEGER: tse.IntAdapter,
        SlashOptionType.BOOLEAN: tse.StringAdapter,
        SlashOptionType.USER: tse.MemberAdapter,
        SlashOptionType.CHANNEL: tse.ChannelAdapter,
        SlashOptionType.ROLE: tse.SafeObjectAdapter,
    }
    EMPTY_ADAPTER = tse.StringAdapter("")

    def __init__(self):
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
            tse.LooseVariableGetterBlock(),
            tse.SubstringBlock(),
            tse.EmbedBlock(),
            tse.ReplaceBlock(),
            tse.PythonBlock(),
            tse.RequireBlock(),
            tse.BlacklistBlock(),
            tse.URLEncodeBlock(),
            tse.CommandBlock(),
            tse.RedirectBlock(),
        ]
        slash_blocks = [HideBlock()]
        self.engine = tse.Interpreter(tse_blocks + slash_blocks)

        self.role_converter = commands.RoleConverter()
        self.channel_converter = commands.TextChannelConverter()
        self.member_converter = commands.MemberConverter()
        self.emoji_converter = commands.EmojiConverter()
        super().__init__()

    @staticmethod
    async def delete_quietly(message: discord.Message):
        try:
            await message.delete()
        except discord.HTTPException:
            pass

    def get_adapter(
        self, option_type: SlashOptionType, default: tse.Adapter = tse.StringAdapter
    ) -> tse.Adapter:
        return self.OPTION_ADAPTERS.get(option_type, default)

    def handle_seed_variables(self, interaction: InteractionCommand, seed_variables: dict) -> dict:
        seed_variables = seed_variables.copy()
        for option in interaction.options:
            adapter = self.get_adapter(option.type)
            try:
                seed_variables[option.name] = adapter(option.value)
            except Exception as exc:
                log.exception(
                    "Failed to initialize adapter %r for option %r:" % (adapter, option),
                    exc_info=exc,
                )
                seed_variables[option.name] = tse.StringAdapter(option.value)

        for original_option in interaction.command.options:
            if original_option.name not in seed_variables:
                log.debug("optional option %s not found, using empty adapter" % original_option)
                seed_variables[original_option.name] = self.EMPTY_ADAPTER
        return seed_variables

    async def process_tag(
        self,
        interaction: InteractionCommand,
        tag: SlashTag,
        *,
        seed_variables: dict = {},
        **kwargs,
    ) -> str:
        log.debug("processing tag %s | options: %r" % (tag, interaction.options))
        seed_variables = self.handle_seed_variables(interaction, seed_variables)

        guild = interaction.guild
        author = interaction.author
        channel = interaction.channel

        tag_author = tse.MemberAdapter(author)
        tag_channel = tse.ChannelAdapter(channel)
        seed = {
            "author": tag_author,
            "channel": tag_channel,
        }
        if guild:
            tag_guild = tse.GuildAdapter(guild)
            seed["server"] = tag_guild
        seed_variables.update(seed)

        output = tag.run(self.engine, seed_variables=seed_variables, **kwargs)
        await tag.update_config()
        to_gather = []
        content = output.body[:2000] if output.body else None
        actions = output.actions

        embed = actions.get("embed")
        hidden = actions.get("hide", False)

        try:
            await self.handle_requires(interaction, actions)
        except RequireCheckFailure:
            return

        if content or embed:
            await self.send_tag_response(interaction, actions, content, hidden=hidden, embed=embed)
        else:
            await interaction.defer(hidden=hidden)

        if command_task := await self.handle_commands(interaction, actions):
            to_gather.append(command_task)

        if to_gather:
            await asyncio.gather(*to_gather)

        if not interaction.completed:
            await interaction.send("Slash Tag completed.", hidden=True)

    async def handle_requires(self, interaction: InteractionCommand, actions: dict):
        try:
            await self.validate_checks(interaction, actions)
        except RequireCheckFailure as error:
            response = error.response
            if response is not None and (response := response.strip()):
                await interaction.send(response[:2000], hidden=True)
            else:
                await interaction.send("You aren't allowed to use this tag.", hidden=True)
            raise

    async def handle_commands(
        self, interaction: InteractionCommand, actions: dict
    ) -> Optional[asyncio.Task]:
        commands = actions.get("commands")
        if not commands:
            return

        command_messages = []
        prefix = (await self.bot.get_valid_prefixes(interaction.guild))[0]
        for command in commands:
            message = FakeMessage.from_interaction(interaction, prefix + command)
            command_messages.append(message)

        silent = actions.get("silent", False)
        overrides = actions.get("overrides")
        return self.create_task(
            self.process_commands(interaction, command_messages, silent, overrides)
        )

    async def process_commands(
        self,
        interaction: InteractionCommand,
        messages: List[discord.Message],
        silent: bool,
        overrides: dict,
    ):
        command_tasks = []
        for message in messages:
            command_task = self.create_task(
                self.process_command(interaction, message, silent, overrides)
            )
            command_tasks.append(command_task)
            await asyncio.sleep(0.1)
        await asyncio.gather(*command_tasks)

    async def process_command(
        self,
        interaction: InteractionCommand,
        command_message: discord.Message,
        silent: bool,
        overrides: dict,
    ):
        ctx = await self.bot.get_context(
            command_message, cls=partial(SlashContext, interaction=interaction)
        )
        if ctx.valid:
            if overrides:
                command = copy(ctx.command)
                # command = commands.Command()
                # command = ctx.command.copy() # does not work as it makes ctx a regular argument
                requires: RS = copy(command.requires)
                priv_level = requires.privilege_level
                if priv_level not in (
                    PL.NONE,
                    PL.BOT_OWNER,
                    PL.GUILD_OWNER,
                ):
                    if overrides["admin"] and priv_level is PL.ADMIN:
                        requires.privilege_level = PL.NONE
                    elif overrides["mod"] and priv_level is PL.MOD:
                        requires.privilege_level = PL.NONE
                if overrides["permissions"] and requires.user_perms:
                    requires.user_perms = discord.Permissions.none()
                command.requires = requires
                ctx.command = command
            await self.bot.invoke(ctx)

    async def send_tag_response(
        self,
        interaction: InteractionCommand,
        actions: dict,
        content: str = None,
        *,
        embed: discord.Embed = None,
        **kwargs,
    ) -> Optional[discord.Message]:
        destination = interaction

        if target := actions.get("target"):
            if target == "dm":
                destination = interaction.author
                del kwargs["hidden"]
            elif target == "reply":
                pass
            else:
                try:
                    chan = await self.channel_converter.convert(interaction, target)
                except commands.BadArgument:
                    pass
                else:
                    if chan.permissions_for(interaction.me).send_messages:
                        destination = chan
                        del kwargs["hidden"]

        if not (content or embed is not None):
            return

        try:
            return await destination.send(content, embed=embed, **kwargs)
        except discord.HTTPException as exc:
            log.exception(
                f"Error sending to destination:{destination!r} for interaction:{interaction!r}\nkwargs:{kwargs!r}",
                exc_info=exc,
            )

    async def validate_checks(self, ctx: commands.Context, actions: dict):
        to_gather = []
        if requires := actions.get("requires"):
            to_gather.append(self.validate_requires(ctx, requires))
        if blacklist := actions.get("blacklist"):
            to_gather.append(self.validate_blacklist(ctx, blacklist))
        if to_gather:
            await asyncio.gather(*to_gather)

    async def validate_requires(self, ctx: commands.Context, requires: dict):
        # sourcery skip: merge-duplicate-blocks
        for argument in requires["items"]:
            role_or_channel = await self.role_or_channel_convert(ctx, argument)
            if not role_or_channel:
                continue
            if isinstance(role_or_channel, discord.Role):
                if role_or_channel in ctx.author.roles:
                    return
            else:
                if role_or_channel == ctx.channel:
                    return
        raise RequireCheckFailure(requires["response"])

    async def validate_blacklist(self, ctx: commands.Context, blacklist: dict):
        # sourcery skip: merge-duplicate-blocks
        for argument in blacklist["items"]:
            role_or_channel = await self.role_or_channel_convert(ctx, argument)
            if not role_or_channel:
                continue
            if isinstance(role_or_channel, discord.Role):
                if role_or_channel in ctx.author.roles:
                    raise RequireCheckFailure(blacklist["response"])
            else:
                if role_or_channel == ctx.channel:
                    raise RequireCheckFailure(blacklist["response"])

    async def role_or_channel_convert(self, ctx: commands.Context, argument: str):
        objects = await asyncio.gather(
            self.role_converter.convert(ctx, argument),
            self.channel_converter.convert(ctx, argument),
            return_exceptions=True,
        )
        objects = [obj for obj in objects if isinstance(obj, (discord.Role, discord.TextChannel))]
        return objects[0] if objects else None

    async def slash_eval(self, interaction: InteractionCommand):
        if not await self.bot.is_owner(interaction.author):
            return await interaction.send("Only bot owners may eval.", hidden=True)
        await interaction.defer()
        ctx = SlashContext.from_interaction(interaction)
        dev = dev_check(self)
        await dev._eval(ctx, body=interaction.options[0].value)
