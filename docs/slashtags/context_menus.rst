=============
Context Menus
=============

SlashTags also supports adding context menu commands. These can be added with ``[p]slashtag user``
or ``[p]slashtags message``. Context menu commands differ from slash commands as they are
invoked through the ``Apps`` section on a message/user context menu.

You can only add 5 global and 5 server context menu commands for each type.

----------------------
Context Menu Arguments
----------------------

Context menu commands do not allow for custom argument creation. They do however have two variables
that are automatically accessible in the tagscript:

*   ``{target_id}`` - representing the ID of the object context menu that invoked the command
*   ``{user}`` - the user that the command was ran on, if a user command was invoked
*   ``{message}`` - the message that the command was ran on, if a message command was invoked
