.. role:: python(code)
    :language: python

===============
Discord Blocks
===============

------------
Author Block
------------

.. autoclass:: tags.adapters.MemberAdapter

------------
Target Block
------------

.. class:: target

    The ``{target}`` block follows the same usage and has the same attributes as the :any:`tags.adapters.MemberAdapter` block, but it defaults to the mentioned user in the tag invocation message if any users are mentioned, or the tag author.

    **Aliases:** ``{member}``

-------------
Channel Block
-------------

.. autoclass:: tags.adapters.TextChannelAdapter

------------
Server Block
------------

.. autoclass:: tags.adapters.GuildAdapter