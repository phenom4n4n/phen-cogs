===============
Slash Arguments
===============

SlashTags support up to 10 arguments with multiple types, allowing for flexibility
and advanced user input handling.

----------------
Adding Arguments
----------------

Similar to the initial slash tag creation process, adding arguments to slash tags follows an
interactive setup. You can either choose to add arguments while creating a slash tag, or by editing
them later with ``[p]slashtag edit arguments <slashtag>``.

--------------
Argument Types
--------------

.. autoclass:: slashtags.SlashOptionType
    :members:

--------------
Argument Usage
--------------

A slash tag's argument can be accessed in its tagscript through the use of a variable block.
For example, if a slash tag has an argument named ``member``, it could be accessed with ``{member}``.

Additionally, slash tag arguments of the channel, role, or user type support attribute
access through the block parameter such as ``{member(nick)}``.
