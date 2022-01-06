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
