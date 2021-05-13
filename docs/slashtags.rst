=========
SlashTags
=========

Slash Tags allow you to create custom `Discord Slash Commands <https://blog.discord.com/slash-commands-are-here-8db0a385d9e6>`_
which harness the power of the TagScriptEngine. If you haven't already, 
it's recommended you also read the :doc:`blocks` page for a general understanding 
of TagScript blocks.

------------
Tag Creation
------------

.. note:: ``[p]`` is your prefix.

Add a tag using the following command::

    [p]slashtag add mytag Hello world!

The bot will then ask for a tag description, for which you can respond with::

    Test slash command.

Afterwards, the bot will ask whether you would like to add arguments to the tag.
In this example, we won't be adding any arguments, so reply no::

    no

Invoke the slash tag with a ``/``::

    /mytag

The bot will then respond with the tag's tagscript::

    Hello world!

^^^^^^^^^^^^^^^^^
Default Variables
^^^^^^^^^^^^^^^^^

Tags come with built-in variable blocks you can access for more information about the invocation context.
These are:

*   ``author``
*   ``channel``
*   ``server``

You can see attributes available using these blocks in :doc:`default_variables`.
