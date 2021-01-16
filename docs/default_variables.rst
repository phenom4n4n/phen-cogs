.. role:: python(code)
    :language: python

=================
Default Variables
=================

The following blocks will be present and accessable as defaults when running any tag.

--------------
Meta Variables
--------------

Meta variables reference meta attributes about the tag invocation.

.. _ArgsBlock:

^^^^^^^^^^
Args Block
^^^^^^^^^^

.. autoclass:: TagScriptEngine.adapter.StringAdapter

    The ``{args}`` block represents the arguments passed after the tag name when invoking 
    a tag. If no parameter is passed, it returns all the text after the invocation name.
    If an index is passed, it will split the arguments into a list by the given splitter, 
    and return the word at that index. The default splitter is a " ".

    **Usage:** ``{args([index]):[splitter]>}``

    **Payload:** splitter

    **Parameter:** index

    **Examples:** 

    In the following examples, assume the tag's name is ``argstag`` and the message 
    content is ``[p]argstag My dog is cute! Would you like to see a photo?``. ::

        {args}
        # My dog is cute! Would you like to see a photo?

        {args(1)}
        # My

        {args(2):!}
        # Would you like to see a photo?

^^^^^^^^^^
Uses Block
^^^^^^^^^^

.. autoclass:: TagScriptEngine.adapter.IntAdapter

    The ``{uses}`` block returns the number of times a tag has been used.

    **Usage:** ``{uses}``

    **Payload:** None

    **Parameter:** None

    **Examples:** ::

        {uses}
        # 1

------------------------
Discord Object Variables
------------------------

These blocks reference Discord objects from the tag invocation context.

.. _AuthorBlock:

^^^^^^^^^^^^
Author Block
^^^^^^^^^^^^

.. autoclass:: tags.adapters.MemberAdapter

^^^^^^^^^^^^
Target Block
^^^^^^^^^^^^

    The ``{target}`` block follows the same usage and has the same attributes as the 
    :ref:`AuthorBlock`, but it defaults to the mentioned user in the tag 
    invocation message if any users are mentioned, or the tag author.

    **Usage:** ``{target}``

    **Aliases:** ``{member}``

^^^^^^^^^^^^^
Channel Block
^^^^^^^^^^^^^

.. autoclass:: tags.adapters.TextChannelAdapter

^^^^^^^^^^^^
Server Block
^^^^^^^^^^^^

.. autoclass:: tags.adapters.GuildAdapter