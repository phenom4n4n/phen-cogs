"""
MIT License

Copyright (c) 2020-present phenom4n4n

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
import inspect
import logging
import textwrap
import traceback
from typing import List

import discord
import TagScriptEngine as tse
from redbot.core import Config, commands
from redbot.core.dev_commands import Dev, async_compile, cleanup_code, get_pages
from redbot.core.utils import AsyncIter

from ..abc import MixinMeta
from ..blocks import ContextVariableBlock, ConverterBlock
from ..errors import BlockCompileError
from ..objects import Tag
from ..utils import menu
from ..views import ConfirmationView

log = logging.getLogger("red.phenom4n4n.tags.owner")


class OwnerCommands(MixinMeta):
    def __init__(self):
        self.custom_command_engine = tse.Interpreter([ContextVariableBlock(), ConverterBlock()])
        super().__init__()

    async def compile_blocks(self, data: dict = None) -> List[tse.Block]:
        blocks = []
        blocks_data = data["blocks"] if data else await self.config.blocks()
        for block_code in blocks_data.values():
            block = self.compile_block(block_code)
            blocks.append(block)
        return blocks

    def compile_block(self, code: str) -> tse.Block:
        to_compile = "def func():\n%s" % textwrap.indent(code, "  ")
        compiled = async_compile(to_compile, "<string>", "exec")
        env = globals().copy()
        env["bot"] = self.bot
        env["tags"] = self
        exec(compiled, env)
        result = env["func"]()
        if not (inspect.isclass(result) and issubclass(result, tse.Block)):
            raise BlockCompileError(f"code must return a {tse.Block}, not {type(result)}")
        log.debug("compiled block, result: %r", result)
        return result

    @staticmethod
    def test_block(block: tse.Block):
        interpreter = tse.Interpreter([block()])
        interpreter.process("{test}")

    @commands.is_owner()
    @commands.group(aliases=["tagset"])
    async def tagsettings(self, ctx: commands.Context):
        """Manage Tags cog settings."""

    @tagsettings.command("settings")
    async def tagsettings_settings(self, ctx: commands.Context):
        """
        View Tags settings.
        """
        data = await self.config.all()
        description = [
            f"**AsyncInterpreter**: `{data['async_enabled']}`",
            f"**Dot Parameter Parsing**: `{data['dot_parameter']}`",
            f"**Custom Blocks**: `{len(data['blocks'])}`",
        ]
        embed = discord.Embed(
            title="Tags Settings",
            color=await ctx.embed_color(),
            description="\n".join(description),
        )
        await ctx.send(embed=embed)

    @tagsettings.group("block")
    async def tagsettings_block(self, ctx: commands.Context):
        """
        Manage custom TagScript blocks.
        """

    @tagsettings_block.command("add")
    async def tagsettings_block_add(self, ctx: commands.Context, name: str, *, code: cleanup_code):
        """
        Add a custom block to the TagScript interpreter.

        The passed code must return a block class that inherits from `TagScriptEngine.Block`.
        """
        try:
            block = self.compile_block(code)
            self.test_block(block)
        except SyntaxError as e:
            if e.text is None:
                error = get_pages("{0.__class__.__name__}: {0}".format(e))
            else:
                error = get_pages(
                    "{0.text}\n{1:>{0.offset}}\n{2}: {0}".format(e, "^", type(e).__name__)
                )
            return await ctx.send_interactive(error)
        except Exception as e:
            exc = traceback.format_exception(e.__class__, e, e.__traceback__)
            response = Dev.sanitize_output(ctx, exc)
            return await ctx.send_interactive(get_pages(response), box_lang="py")

        async with self.config.blocks() as b:
            b[name] = code
        await self.initialize_interpreter()
        await ctx.send(f"Added block `{block.__name__}` to the Tags interpreter.")

    @tagsettings_block.command("remove", aliases=["delete"])
    async def tagsettings_block_remove(self, ctx: commands.Context, name: str):
        """
        Remove a custom block from the TagScript interpreter.
        """
        async with self.config.blocks() as b:
            if name not in b:
                return await ctx.send("That block doesn't exist.")
            del b[name]
        await self.initialize_interpreter()
        await ctx.send(f"Deleted block `{name}`.")

    @tagsettings_block.command("list")
    async def tagsettings_block_list(self, ctx: commands.Context):
        """
        List all custom blocks in the TagScript interpreter.
        """
        blocks = await self.config.blocks()
        if not blocks:
            return await ctx.send("No custom blocks found.")
        description = [f"`{name}` - {len(code)} characters" for name, code in blocks.items()]
        embed = discord.Embed(
            title="Custom TagScript Blocks",
            color=await ctx.embed_color(),
            description="\n".join(description),
        )
        await menu(ctx, [embed])

    @tagsettings_block.command("show")
    async def tagsettings_block_show(self, ctx: commands.Context, name: str):
        """
        Show the code of a custom block.
        """
        blocks = await self.config.blocks()
        if not blocks:
            return await ctx.send("No custom blocks found.")
        try:
            code = blocks[name]
        except KeyError:
            return await ctx.send("That block doesn't exist.")
        await ctx.send_interactive(get_pages(code), box_lang="py")

    @tagsettings.command("async")
    async def tagsettings_async(self, ctx: commands.Context, true_or_false: bool = None):
        """
        Toggle using the asynchronous TagScript interpreter.

        If you aren't a developer or don't know what this is, there's no reason for you to change it.
        """
        target_state = true_or_false if true_or_false is not None else not self.async_enabled
        await self.config.async_enabled.set(target_state)
        await self.initialize_interpreter()
        asynchronous = "asynchronous" if target_state else "synchronous"
        await ctx.send(f"The TagScript interpreter is now {asynchronous}.")

    @tagsettings.command("dotparam")
    async def tagsettings_dotparam(self, ctx: commands.Context, true_or_false: bool = None):
        """
        Toggle the TagScript parsing style.

        If `dot_parameter` is enabled, TagScript blocks will parse like this:
        `{declaration.parameter:payload}`
        instead of:
        `{declaration(parameter):payload}`
        """
        target_state = true_or_false if true_or_false is not None else not self.dot_parameter
        await self.config.dot_parameter.set(target_state)
        await self.initialize_interpreter()
        enabled = "enabled" if target_state else "disabled"
        parameter = ".parameter" if target_state else "(parameter)"
        await ctx.send(
            f"`dot parameter` parsing has been {enabled}.\n"
            "Blocks will be parsed like this: `{declaration%s:payload}`." % parameter
        )

    @commands.is_owner()
    @commands.command()
    async def migratealias(self, ctx: commands.Context):
        """
        Migrate the Alias cog's global and server aliases into tags.

        This converts all aliases created with the Alias cog into tags with command blocks.
        This action cannot be undone.

        **Example:**
        `[p]migratealias`
        """
        msg = "Are you sure you want to migrate Alias data to tags?"
        if not await ConfirmationView.confirm(ctx, msg, cancel_message="Migration cancelled."):
            return

        migrated_guilds = 0
        migrated_guild_alias = 0
        alias_config = Config.get_conf(
            None, 8927348724, cog_name="Alias"  # core cog doesn't use force_registration=True smh
        )  # Red can't change these values without breaking data
        # so while this is sus it is technically safe to use
        alias_config.register_global(entries=[])
        all_guild_data: dict = await alias_config.all_guilds()

        async for guild_data in AsyncIter(all_guild_data.values(), steps=100):
            if not guild_data["entries"]:
                continue
            migrated_guilds += 1
            for alias in guild_data["entries"]:
                tagscript = "{c:%s {args}}" % alias["command"]
                tag = Tag(
                    self,
                    alias["name"],
                    tagscript,
                    author_id=alias["creator"],
                    guild_id=alias["guild"],
                    uses=alias["uses"],
                )
                await tag.initialize()
                migrated_guild_alias += 1
        await ctx.send(
            f"Migrated {migrated_guild_alias} aliases from {migrated_guilds} "
            "servers to tags. Moving on to global aliases.."
        )

        migrated_global_alias = 0
        async for entry in AsyncIter(await alias_config.entries(), steps=50):
            tagscript = "{c:%s {args}}" % entry["command"]
            global_tag = Tag(
                self,
                entry["name"],
                tagscript,
                author_id=entry["creator"],
                uses=entry["uses"],
            )
            await global_tag.initialize()
            migrated_global_alias += 1
        await ctx.send(f"Migrated {migrated_global_alias} global aliases to tags.")

    def parse_cc_text(self, content: str) -> str:
        output = self.custom_command_engine.process(content)
        return output.body

    def convert_customcommand(self, guild_id: int, name: str, custom_command: dict) -> Tag:
        author_id = custom_command.get("author", {"id": None})["id"]
        response = custom_command["response"]
        if isinstance(response, str):
            tagscript = self.parse_cc_text(response)
        else:
            tag_lines = []
            indices = []
            for index, response_text in enumerate(response, 1):
                script = self.parse_cc_text(response_text)
                tag_lines.append("{=(choice.%s):%s}" % (index, script))
                indices.append(index)
            random_block = "{#:%s}" % ",".join(str(i) for i in indices)
            tag_lines.append("{=(chosen):%s}" % random_block)
            tag_lines.append("{choice.{chosen}}")
            tagscript = "\n".join(tag_lines)
        return Tag(self, name, tagscript, guild_id=guild_id, author_id=author_id)

    @commands.is_owner()
    @commands.command(aliases=["migratecustomcommands"])
    async def migratecustomcom(self, ctx: commands.Context):
        """
        Migrate the CustomCommand cog's server commands into tags.

        This converts all custom commands created into tags with the command text as TagScript.
        Randomized commands are converted into random blocks.
        Commands with converters are converted into indexed args blocks.
        This action cannot be undone.

        **Example:**
        `[p]migratealias`
        """
        msg = "Are you sure you want to migrate CustomCommands data to tags?"
        if not await ConfirmationView.confirm(ctx, msg, cancel_message="Migration cancelled."):
            return

        cc_config = Config.get_conf(None, 414589031223512, cog_name="CustomCommands")
        migrated_guilds = 0
        migrated_ccs = 0
        all_guild_data: dict = await cc_config.all_guilds()

        async for guild_id, guild_data in AsyncIter(all_guild_data.items(), steps=100):
            if not guild_data["commands"]:
                continue
            migrated_guilds += 1
            for name, command in guild_data["commands"].items():
                if not command:
                    continue  # some keys in custom commands config are None instead of being deleted
                try:
                    tag = self.convert_customcommand(guild_id, name, command)
                except Exception as exc:
                    log.exception(
                        "An exception occured while converting custom command %s (%r) from guild %s",
                        name,
                        command,
                        guild_id,
                        exc_info=exc,
                    )
                    return await ctx.send(
                        f"An exception occured while converting custom command `{name}` from "
                        f"server {guild_id}. Check your logs for more details and report this to the cog author."
                    )
                await tag.initialize()
                migrated_ccs += 1
        await ctx.send(
            f"Migrated {migrated_ccs} custom commands from {migrated_guilds} servers to tags."
        )
