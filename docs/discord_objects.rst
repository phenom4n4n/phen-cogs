.. role:: python(code)
    :language: python

===============
Discord Blocks
===============

.. autoclass:: tags.adapters.MemberAdapter

.. class:: target

    The ``{target}`` block follows the same usage and has the same attributes as the :any:`tags.adapters.MemberAdapter` block, but it defaults to the mentioned user in the tag invocation message if any users are mentioned, or the tag author.

    **Aliases:** ``{member}``

.. autoclass:: tags.adapters.TextChannelAdapter

.. autoclass:: tags.adapters.GuildAdapter