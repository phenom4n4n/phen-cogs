=========
SlashTags
=========

Slash Tags allow you to create custom `Discord Slash Commands <https://blog.discord.com/slash-commands-are-here-8db0a385d9e6>`_
which harness the power of the TagScriptEngine.

Block Syntax
------------

``{block(parameter):payload}``

``[arg]`` = Optional

``<arg>`` = Required

Usage
-----
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

Below is an example tag that returns info related to the tag author. ::

    [p]tag add authorinfo Username: **{author}**
    ID: **{author(id)}**
    Creation Date: **{author(created_at)}**
    Bot: **{author(bot)}**

The ``args`` block can be useful for customizing tags and works well with the :ref:`CommandBlock`.
Simple echo command that validates if args were provided::

    [p]tag add echo {if({args}==):You must provide text to echo.|{args}}

Here's a tag that uses the default variable blocks as well as the :ref:`IfBlock`::

    [p]tag add startertag Hi, this is an example of a tag.
    This tag will now invoke a ping command.
    {c:ping}
    {delete({args(0)}==delete)}
    {embed({
        "title":"The server this was invoked on was {server}.",
        "description":"{if({args}==):You did not provide any arguments for this tag|The arguments provided were: `{args}`}",
        "thumbnail":{"url":"{guild(icon)}"},
        "author":{"name":"{author} invoked this tag.","icon_url":"{author(avatar)}"},
        "color":2105893,
        "footer":{"icon_url":"{author(avatar)}","text":"{target} is the target of this tag."}
    })}
