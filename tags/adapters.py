from TagScriptEngine import Verb
from TagScriptEngine.interface import Adapter
from discord import Member, TextChannel, Guild


class MemberAdapter(Adapter):
    """
    The ``{author}`` block with no parameters returns the tag invoker's full username
    and discriminator, but passing the attributes listed below to the block payload
    will return that attribute instead.

    **Aliases:** ``user``

    **Usage:** ``{author([attribute])``

    **Payload:** None

    **Parameter:** attribute, None

    **Attributes:**

    id
        The author's Discord ID.
    name
        The author's username.
    nick
        The author's nickname, if they have one, else their username.
    avatar
        A link to the author's avatar, which can be used in embeds.
    discriminator
        The author's discriminator.
    created_at
        The author's account creation date.
    joined_at
        The date the author joined the server.
    mention
        A formatted text that pings the author.
    bot
        Whether or not the author is a bot.
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
    The ``{channel}`` block with no parameters returns the channel's full name
    but passing the attributes listed below to the block payload
    will return that attribute instead.

    **Usage:** ``{channel([attribute])``

    **Payload:** None

    **Parameter:** attribute, None

    **Attributes:**

    id
        The channel's ID.
    name
        The channel's name.
    created_at
        The channel's creation date.
    nsfw
        Whether the channel is nsfw.
    mention
        A formatted text that pings the channel.
    topic
        The channel's topic.
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
    The ``{author}`` block with no parameters returns the server's name
    but passing the attributes listed below to the block payload
    will return that attribute instead.

    **Aliases:** ``guild``

    **Usage:** ``{server([attribute])``

    **Payload:** None

    **Parameter:** attribute, None

    **Attributes:**

    id
        The server's ID.
    name
        The server's name.
    icon
        A link to the server's icon, which can be used in embeds.
    created_at
        The server's creation date.
    member_count
        The server's member count.
    description
        The server's description if one is set, or "No description".
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

class IntegerAdapter(Adapter):
    def __init__(self, number: int):
        self.number = number

    def get_value(self, ctx: Verb) -> str:
        return str(self.number)