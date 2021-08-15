============
Example Tags
============

The following tags listed show examples of using tagscript blocks.

Context Variables Example
-------------------------

The following tag shows an example of using the various attributes listed in :doc:`default_variables`.

::

    [p]tag + introduce Hi {user(nick)}, welcome to **{guild}**!

    __**USER BLOCK USAGE**__
    Your username is {user(name)}, discriminator is {user(discriminator)}, id is {user(id)}.
    Your account was created at {user(created_at)} and you joined {guild(name)} on {user(joined_at)}.
    The color for your highest role is {user(color)}.

    __**SERVER BLOCK USAGE**__
    The id of this server is {server(id)}, and it was created at {server(created_at)}.
    *Some stats about the server:*
    Member count: {server(member_count)}
    Human Count: {server(humans)}
    Bot Count: {server(bots)}
    Additional Info about Server: {server(description)}

    {server(random)} is a just random member of the server you might want to say hi.

    __**CHANNEL BLOCK USAGE**__
    The channel you are using this tag in is {channel(name)} and channel id is {channel(id)}.
    Alternatively you could use this attribute in your tags to jump to other channels {channel(mention)}
    The channel was created at {channel(created_at)} and the NSFW status of this channel is: {channel(nsfw)}
    __*Channel Topic:*__ {channel(topic)}

Information Storage Example
---------------------------

This simple tag shows how to store repeated/informational text. This tag has often been used in a
support server.

::

    [p] tag + ss Please send a screenshot. It’s much easier to figure out your problem if we can see what went wrong.

Command Alias Example
---------------------

The following tag is a simple example of using a tag to add an alias to a command.

::

    [p]tag add gstart {c:giveaway start {args}}
