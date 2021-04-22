import asyncio
from copy import copy
from functools import partial
from typing import List, Optional

import discord
from redbot.core import commands
import TagScriptEngine as tse

from .abc import MixinMeta
from .errors import (BlacklistCheckFailure, MissingTagPermissions,
                     RequireCheckFailure, WhitelistCheckFailure)
from .models import InteractionResponse, SlashOptionType
from .objects import SlashTag, FakeMessage, SlashContext
from .utils import dev_check

empty_adapter = tse.StringAdapter("")

PL = commands.PrivilegeLevel
RS = commands.Requires


class Processor(MixinMeta):
    OPTION_ADAPTERS = {
        SlashOptionType.STRING: tse.StringAdapter,
        SlashOptionType.INTEGER: tse.IntAdapter,
        SlashOptionType.BOOLEAN: tse.StringAdapter,
        SlashOptionType.USER: tse.MemberAdapter,
        SlashOptionType.CHANNEL: tse.ChannelAdapter,
        SlashOptionType.ROLE: tse.SafeObjectAdapter,
    }

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

    async def process_tag(
        self,
        interaction: InteractionResponse,
        tag: SlashTag,
        *,
        seed_variables: dict = {},
        **kwargs,
    ) -> str:
        for option in interaction.options:
            seed_variables[option.name] = self.get_adapter(option.type)(option.value)
        for original_option in interaction.command.options:
            if original_option.name not in seed_variables:
                seed_variables[original_option.name] = empty_adapter

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
        command_messages = []
        hide = actions.get("hide", False)
        destination = interaction
        ctx = interaction
        # SlashContext.from_interaction ?

        if actions:
            try:
                await self.validate_checks(ctx, actions)
            except RequireCheckFailure as error:
                response = error.response
                if response is not None and response.strip():
                    await ctx.send(response[:2000], hidden=True)  # used hide?
                return

        if commands := actions.get("commands"):
            prefix = (await self.bot.get_valid_prefixes(interaction.guild))[0]
            for command in commands:
                message = FakeMessage.from_interaction(interaction, prefix + command)
                command_messages.append(message)

        # this is going to become an asynchronous swamp
        if content or embed is not None:
            await self.send_tag_response(destination, content, embed=embed, hidden=hide)
        else:
            await interaction.defer()

        if command_messages:
            silent = actions.get("silent", False)
            overrides = actions.get("overrides")
            to_gather.append(
                self.process_commands(interaction, command_messages, silent, overrides)
            )

        if to_gather:
            await asyncio.gather(*to_gather)

    async def process_commands(
        self,
        interaction: InteractionResponse,
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
        interaction: InteractionResponse,
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
        destination: discord.abc.Messageable,
        content: str = None,
        **kwargs,
    ) -> Optional[discord.Message]:
        try:
            return await destination.send(content, **kwargs)
        except discord.HTTPException:
            pass

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

    async def slash_eval(self, interaction: InteractionResponse):
        await interaction.defer()
        if not await self.bot.is_owner(interaction.author):
            return await interaction.send("Only bot owners may eval.", hidden=True)
        ctx = SlashContext.from_interaction(interaction)
        dev = dev_check(self)
        await dev._eval(ctx, body=interaction.options[0].value)
