from TagScriptEngine import Verb
from TagScriptEngine.interface import Adapter
from discord import Member, TextChannel, Guild


class MemberAdapter(Adapter):
    """
    Aliases: `user`

    Usage: `{author([attribute])`

    Payload: None

    Parameter: attribute, None

    By default this will return the tag invoker's full username. Certain attributes can be passed to the payload to access more information about the author. These include:

    ```
    id
    name
    nick
    avatar
    discriminator
    created_at
    joined_at
    mention
    bot
    ```
    """

    def __init__(self, member: Member):
        self.member = member
        self.attributes = {
            "id": member.id,
            "name": member.name,
            "nick": member.display_name,
            "avatar": member.avatar_url,
            "discriminator": member.discriminator,
            "created_at": member.created_at,
            "joined_at": member.joined_at,
            "mention": member.mention,
            "bot": member.bot,
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
    """
    Usage: `{channel([attribute])`

    Payload: None

    Parameter: attribute, None

    By default this will return the tag's invoke channel name. Certain attributes can be passed to the payload to access more information about the channel. These include:

    ```
    id
    name
    discriminator
    created_at
    nsfw
    mention
    topic
    ```
    """

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
    """
    Aliases: `guild`

    Usage: `{server([attribute])`

    Payload: None

    Parameter: attribute, None

    By default this will return the tag's invoke server name. Certain attributes can be passed to the payload to access more information about the server. These include:

    ```
    id
    name
    nick
    icon
    discriminator
    member_count
    description
    ```
    """

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
