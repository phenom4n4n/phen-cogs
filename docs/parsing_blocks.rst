==============
Parsing Blocks
==============

Parsing blocks interact with the tag invocation and affect the tag's 
output in Discord.

------------------
Restriction Blocks
------------------

The following blocks allow for restriction of tags behind roles or 
channels, or setting tag cooldowns (soon).

^^^^^^^^^^^^^
Require Block
^^^^^^^^^^^^^

.. autoclass:: tags.blocks.RequireBlock

^^^^^^^^^^^^^^^
Blacklist Block
^^^^^^^^^^^^^^^

.. autoclass:: tags.blocks.BlacklistBlock

--------------
Message Blocks
--------------

Message blocks modify the tag's output.

^^^^^^^^^^^
Embed Block
^^^^^^^^^^^

.. autoclass:: tags.blocks.EmbedBlock

^^^^^^^^^^^^^^
Redirect Block
^^^^^^^^^^^^^^

.. autoclass:: tags.blocks.RedirectBlock

^^^^^^^^^^^^
Delete Block
^^^^^^^^^^^^

.. autoclass:: tags.blocks.DeleteBlock

^^^^^^^^^^^^^^
React Block
^^^^^^^^^^^^^^

.. autoclass:: tags.blocks.ReactBlock

^^^^^^^^^^^^^^
ReactU Block
^^^^^^^^^^^^^^

.. autoclass:: tags.blocks.ReactUBlock

--------------
Utility Blocks
--------------

The following utility blocks extend the power of tags that interface 
with bot commands.

.. _CommandBlock:

^^^^^^^^^^^^^
Command Block
^^^^^^^^^^^^^

.. autoclass:: tags.blocks.CommandBlock
