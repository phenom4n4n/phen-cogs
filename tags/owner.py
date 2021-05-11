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
import asyncio
from typing import List
import textwrap
import traceback
import inspect
import logging

import TagScriptEngine as tse
from redbot.core import commands, Config
from redbot.core.dev_commands import Dev
from redbot.core.utils import AsyncIter
from redbot.core.utils.predicates import MessagePredicate

from .abc import MixinMeta
from .errors import BlockCompileError
from .objects import Tag

log = logging.getLogger("red.phenom4n4n.owner")

class OwnerCommands(MixinMeta):
    async def compile_blocks(self) -> List[tse.Block]:
        blocks = []
        blocks_data = await self.config.blocks()
        for block_code in blocks_data.values():
            block = self.compile_block(block_code)
            blocks.append(block)
        return blocks

    def compile_block(self, code: str) -> tse.Block:
        to_compile = "def func():\n%s" % textwrap.indent(code, "  ")
        compiled = Dev.async_compile(to_compile, "<string>", "exec")
        env = globals().copy()
        exec(compiled, env)
        result = env["func"]()
        if not (inspect.isclass(result) or issubclass(result, tse.Block)):
            raise BlockCompileError(f"code must return a {tse.Block}, not {type(result)}")
        log.debug("compiled block, result: %r" % result)
        return result

    @staticmethod
    def test_block(block: tse.Block):
        interpreter = tse.Interpreter([block()])
        interpreter.process("{test}")

    @commands.is_owner()
    @commands.group(aliases=["tagset"])
    async def tagsettings(self, ctx: commands.Context):
        """Manage Tags cog settings."""

    @tagsettings.command("addblock")
    async def tagsettings_addblock(self, ctx: commands.Context, name: str, *, code: Dev.cleanup_code):
        """
        Add a custom block to the TagScript interpreter.
        
        The passed code must return a block class that inherits from `TagScriptEngine.Block`.
        """
        try:
            block = self.compile_block(code)
            self.test_block(block)
        except SyntaxError as e:
            return await ctx.send(Dev.get_syntax_error(e))
        except Exception as e:
            response = traceback.format_exc()
            response = Dev.sanitize_output(ctx, response)
            return await ctx.send_interactive(Dev.get_pages(response), box_lang="py")

        async with self.config.blocks() as b:
            b["name"] = code
        await self.initialize_interpreter()
        await ctx.send(f"Added block `{block.__name__}` to the Tags interpreter.")

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
        await ctx.send(f"Are you sure you want to migrate Alias data to tags? (Y/n)")
        pred = MessagePredicate.yes_or_no(ctx)
        try:
            await self.bot.wait_for("message", check=pred, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send("Query timed out, not migrating alias to tags.")
        if pred.result is False:
            return await ctx.send("Migration cancelled.")

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
        tagscript = output.body
        return tagscript

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
        await ctx.send(f"Are you sure you want to migrate CustomCommands data to tags? (Y/n)")
        pred = MessagePredicate.yes_or_no(ctx)
        try:
            await self.bot.wait_for("message", check=pred, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send("Query timed out, not migrating CustomCommands to tags.")
        if pred.result is False:
            return await ctx.send("Migration cancelled.")

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
                        "An exception occured while converting custom command %s (%r) from guild %s"
                        % (name, command, guild_id),
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
