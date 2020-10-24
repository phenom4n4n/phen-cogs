from TagScriptEngine import Verb
from TagScriptEngine.interface import Adapter
from discord import Member, TextChannel, Guild


class MemberAdapter(Adapter):
    def __init__(self, member: Member):
        self.member = member
        self.attributes = {
            "id": member.id,
            "name": member.name,
            "nick": member.nick,
            "avatar": member.avatar_url,
            "discriminator": member.discriminator,
            "created_at": member.created_at,
            "joined_at": member.joined_at,
            "mention": member.mention,
        }

    def get_value(self, ctx: Verb) -> str:
        if ctx.parameter == None:
            return str(self.member)
        param = self.attributes.get(ctx.parameter, None)
        if param is not None:
            return str(param)
        else:
            return None


class TextChannelAdapter(Adapter):
    def __init__(self, channel: TextChannel):
        self.channel = channel
        self.attributes = {
            "id": channel.id,
            "name": str(channel),
            "created_at": channel.created_at,
            "nsfw": channel.nsfw,
            "mention": channel.mention,
            "topic": channel.topic or None,
        }

    def get_value(self, ctx: Verb) -> str:
        if ctx.parameter == None:
            return str(self.channel)
        param = self.attributes.get(ctx.parameter, None)
        if param is not None:
            return str(param)
        else:
            return None


class GuildAdapter(Adapter):
    def __init__(self, guild: Guild):
        self.guild = guild
        self.attributes = {
            "id": guild.id,
            "name": str(guild),
            "icon": guild.icon_url,
            "created_at": guild.created_at,
            "member_count": guild._member_count,
            "description": guild.description or "No description.",
        }

    def get_value(self, ctx: Verb) -> str:
        if ctx.parameter == None:
            return str(self.guild)
        param = self.attributes.get(ctx.parameter, None)
        if param is not None:
            return str(param)
        else:
            return None
