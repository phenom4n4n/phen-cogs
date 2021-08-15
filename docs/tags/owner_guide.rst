========================
Tags Owner Configuration
========================

This page details some of the configurability options to Bot owners using the Tags cog.

These settings can be applied with the ``[p]tagset`` group command, and viewed with
``[p]tagset settings``.

-------------
Custom Blocks
-------------

For developers who wish to add custom blocks to the TagScript engine, Tags has built in commands
to add blocks without editing the cog.

Start off with the ``[p]tagset block add <name> <code>`` command. The code passed must subclass
:class:`TagScriptEngine.Block` and return the subclass. Here's an example of a block that returns
a random duck image ::

    [p]tagset block add duck ```py
    import aiohttp

    class RandomDuck(tse.Block):
        ACCEPTED_NAMES = ("duck",)

        async def process(self, ctx: tse.Context):
            async with aiohttp.ClientSession() as session:
                async with session.get("https://random-d.uk/api/v2/random") as resp:
                    data = await resp.json()
            return data["url"]

    return RandomDuck
    ```

When a user runs a tag with a ``duck`` block, it will return a random duck image such as ::

    [p]tag + randomduck {duck}
    [p]randomduck
    # https://random-d.uk/api/121.jpg

One thing to note in the above example is that the `RandomDuck.process` method is asynchronous.
By default, the Tags interpreter doesn't support asynchronous blocks, but asynchronous parsing
can be enabled as detailed in :ref:`Asynchronous Interpreter`.

Custom blocks can be viewed with ``[p]tagset block list`` or ``[p]tagset block show <block_name>``.
They can be deleted with ``[p]tagset block remove <block_name>``, and edited by simply re-adding a
block with the same name.

^^^^^^^^^^^^^^^^^^^^^^^^
Custom Block Environment
^^^^^^^^^^^^^^^^^^^^^^^^

The following global scope variables are available when compiling custom block code:

+-------------+--------------------------------------+
| Name        | Value                                |
+=============+======================================+
| ``tse``     | The TagScriptEngine module.          |
+-------------+--------------------------------------+
| ``asyncio`` | The standard library asyncio module. |
+-------------+--------------------------------------+
| ``bot``     | The bot object.                      |
+-------------+--------------------------------------+
| ``tags``    | The Tags cog object.                 |
+-------------+--------------------------------------+

------------------------
Asynchronous Interpreter
------------------------

By default, the Tags interpreter only supports synchronous blocks and methods. However, in order to
support custom blocks with asynchronous code and avoid blocking tags, bot owners can enable
the asynchronous interpreter with ``[p]tagset async True``. Synchronous blocks will still parse
normally through the interpreter.

-------------
Dot Parameter
-------------

TagScript block parsing can be changed to identify parameters with ``.`` rather than ``()``.
This "dot-parameter" style parsing is similar to other formatting parsers, such as the one used in
**CustomCom**. Enabling this with ``[p]tagset dotparam`` will have the following behavior:

::

    {server.name}
    # Red - Discord Bot

    # dot parameter disabled
    {server(name)}
    # Red - Discord Bot
