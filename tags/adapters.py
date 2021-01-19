from TagScriptEngine import Verb
from TagScriptEngine.interface import Adapter
from discord import Member, TextChannel, Guild


class AttributeAdapter(Adapter):
    def __init__(self, base):
        self.object = base
        self.attributes = {
            "id": self.object.id,
            "created_at": self.object.created_at,
            "timestamp": int(self.object.created_at.timestamp()),
            "name": self.object.name,
        }
        self.update_attributes()

    def update_attributes(self):
        additional_attributes = {}
        self.attributes.update(additional_attributes)

    def get_value(self, ctx: Verb) -> str:
        if ctx.parameter == None:
            return str(self.object)
        param = self.attributes.get(ctx.parameter)
        if param is not None:
            return str(param)
        else:
            return None


class MemberAdapter(AttributeAdapter):
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
    timestamp
        The author's account creation date as a UTC timestamp.
    joined_at
        The date the author joined the server.
    mention
        A formatted text that pings the author.
    bot
        Whether or not the author is a bot.
    """

    def update_attributes(self):
        additional_attributes = {
            "nick": self.object.display_name,
            "avatar": self.object.avatar_url,
            "discriminator": self.object.discriminator,
            "joined_at": self.object.joined_at,
            "mention": self.object.mention,
            "bot": self.object.bot,
        }
        self.attributes.update(additional_attributes)


class TextChannelAdapter(AttributeAdapter):
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
    timestamp
        The channel's creation date as a UTC timestamp.
    nsfw
        Whether the channel is nsfw.
    mention
        A formatted text that pings the channel.
    topic
        The channel's topic.
    """

    def update_attributes(self):
        additional_attributes = {
            "nsfw": self.object.nsfw,
            "mention": self.object.mention,
            "topic": self.object.topic or None,
        }
        self.attributes.update(additional_attributes)


class GuildAdapter(AttributeAdapter):
    """
    The ``{server}`` block with no parameters returns the server's name
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
    timestamp
        The server's creation date as a UTC timestamp.
    member_count
        The server's member count.
    description
        The server's description if one is set, or "No description".
    """

    def update_attributes(self):
        additional_attributes = {
            "icon": self.object.icon_url,
            "member_count": self.object.member_count,
            "description": self.object.description or "No description.",
        }
        self.attributes.update(additional_attributes)
