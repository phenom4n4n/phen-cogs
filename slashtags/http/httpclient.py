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

import json
import logging
from typing import List

import discord

from .models import InteractionCallbackType

log = logging.getLogger("red.phenom4n4n.slashtags.http")


class Route(discord.http.Route):
    BASE = "https://discord.com/api/v8"


class SlashHTTP:
    def __init__(self, cog):
        self.cog = cog
        self.bot = cog.bot
        self.request = cog.bot.http.request

    @property
    def application_id(self):
        return self.cog.application_id

    def add_slash_command(self, command: dict):
        route = Route(
            "POST", "/applications/{application_id}/commands", application_id=self.application_id
        )
        return self.request(route, json=command)

    def edit_slash_command(self, command_id: int, command: dict):
        route = Route(
            "PATCH",
            "/applications/{application_id}/commands/{command_id}",
            application_id=self.application_id,
            command_id=command_id,
        )
        return self.request(route, json=command)

    def remove_slash_command(self, command_id: int):
        route = Route(
            "DELETE",
            "/applications/{application_id}/commands/{command_id}",
            application_id=self.application_id,
            command_id=command_id,
        )
        return self.request(route)

    def get_slash_commands(self):
        route = Route(
            "GET", "/applications/{application_id}/commands", application_id=self.application_id
        )
        return self.request(route)

    def put_slash_commands(self, commands: list):
        route = Route(
            "PUT", "/applications/{application_id}/commands", application_id=self.application_id
        )
        return self.request(route, json=commands)

    def add_guild_slash_command(self, guild_id: int, command: dict):
        route = Route(
            "POST",
            "/applications/{application_id}/guilds/{guild_id}/commands",
            application_id=self.application_id,
            guild_id=guild_id,
        )
        return self.request(route, json=command)

    def edit_guild_slash_command(self, guild_id: int, command_id: int, command: dict):
        route = Route(
            "PATCH",
            "/applications/{application_id}/guilds/{guild_id}/commands/{command_id}",
            application_id=self.application_id,
            guild_id=guild_id,
            command_id=command_id,
        )
        return self.request(route, json=command)

    def remove_guild_slash_command(self, guild_id: int, command_id: int):
        route = Route(
            "DELETE",
            "/applications/{application_id}/guilds/{guild_id}/commands/{command_id}",
            application_id=self.application_id,
            guild_id=guild_id,
            command_id=command_id,
        )
        return self.request(route)

    def get_guild_slash_commands(self, guild_id: int):
        route = Route(
            "GET",
            "/applications/{application_id}/guilds/{guild_id}/commands",
            application_id=self.application_id,
            guild_id=guild_id,
        )
        return self.request(route)

    def put_guild_slash_commands(self, guild_id: int, commands: list):
        route = Route(
            "PUT",
            "/applications/{application_id}/guilds/{guild_id}/commands",
            application_id=self.application_id,
            guild_id=guild_id,
        )
        return self.request(route, json=commands)

    def send_message(
        self,
        token: str,
        interaction_id: int,
        *,
        type: int,
        initial_response: bool,
        content: str = None,
        file: discord.File = None,
        files: List[discord.File] = None,
        embed: discord.Embed = None,
        embeds: List[discord.Embed] = None,
        tts: bool = False,
        allowed_mentions: discord.AllowedMentions = None,
        flags: int = None,
        components: list = None,
    ):
        if embed is not None:
            embeds = [embed]
        if file is not None:
            files = [file]
        if allowed_mentions is None:
            allowed_mentions = self.bot.allowed_mentions

        data = {}
        if content:
            data["content"] = str(content)
        if tts:
            data["tts"] = True
        if embeds:
            data["embeds"] = [e.to_dict() for e in embeds]
        if flags:
            data["flags"] = flags
        if embeds:
            data["embeds"] = [e.to_dict() for e in embeds]
        if flags:
            data["flags"] = flags
        if components is not None:
            data["components"] = [c.to_dict() for c in components]

        payload = {"type": type.value}
        if data:
            data["allowed_mentions"] = allowed_mentions.to_dict()
            payload["data"] = data

        if initial_response:
            url = "/interactions/{interaction_id}/{token}/callback"
            send_data = payload
        else:
            url = "/webhooks/{application_id}/{token}"
            send_data = data

        # logic taken from discord.py
        # https://github.com/Rapptz/discord.py/blob/45d498c1b76deaf3b394d17ccf56112fa691d160/discord/http.py#L462
        form = [{"name": "payload_json", "value": self._to_json(send_data)}]
        if files and len(files) == 1:
            file = files[0]
            form.append(
                {
                    "name": "file",
                    "value": file.fp,
                    "filename": file.filename,
                    "content_type": "application/octet-stream",
                }
            )
        elif files:
            for index, file in enumerate(files):
                form.append(
                    {
                        "name": f"file{index}",
                        "value": file.fp,
                        "filename": file.filename,
                        "content_type": "application/octet-stream",
                    }
                )

        route = Route(
            "POST",
            url,
            interaction_id=interaction_id,
            token=token,
            application_id=self.application_id,
        )

        log.debug("sending response, initial = %r: %r", initial_response, send_data)
        return self.request(route, form=form, files=files)

    def edit_message(
        self,
        token: str,
        message_id: int = None,
        *,
        content: str = ...,
        embed: discord.Embed = None,
        embeds: List[discord.Embed] = None,
        allowed_mentions: discord.AllowedMentions = None,
        original: bool = False,
        components: list = None,
    ):
        url = "/webhooks/{application_id}/{token}/messages/"
        url += "@original" if original else "{message_id}"
        route = Route(
            "PATCH",
            url,
            application_id=self.application_id,
            token=token,
            message_id=message_id,
        )
        if embed is not None:
            embeds = [embed]
        if allowed_mentions is None:
            allowed_mentions = self.bot.allowed_mentions

        payload = {}
        if content is not ...:
            payload["content"] = str(content) if content is not None else None
        if embeds:
            payload["embeds"] = [e.to_dict() for e in embeds]
        if components is not None:
            payload["components"] = [c.to_dict() for c in components]

        payload["allowed_mentions"] = allowed_mentions.to_dict()

        return self.request(route, json=payload)

    def delete_message(self, token: str, message_id: str):
        route = Route(
            "DELETE",
            "/webhooks/{application_id}/{token}/messages/{message_id}",
            application_id=self.application_id,
            token=token,
            message_id=message_id,
        )
        return self.request(route)

    def autocomplete(self, token: str, interaction_id: int, choices: List[dict]):
        route = Route(
            "POST",
            "/interactions/{interaction_id}/{token}/callback",
            token=token,
            interaction_id=interaction_id,
        )
        payload = {
            "type": InteractionCallbackType.application_command_autocomplete_result.value,
            "data": {"choices": choices},
        }
        return self.request(route, json=payload)

    @staticmethod
    def _to_json(obj) -> str:
        return json.dumps(obj, separators=(",", ":"), ensure_ascii=True)
