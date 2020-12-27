# **Tag Documentation**

Welcome to the incomplete TagScript documentation. This will explain the custom TagScript blocks. If a block you are looking for isn't here, then you should check if its in the base [TagScriptEngine docs](https://github.com/JonSnowbd/TagScript).

### **Blocks:**
- require
- blacklist
- redirect
- command
- delete
- silent
- args
- author
- target
- channel
- server
- embed
- react

**Block Syntax:**

`{block(parameter):payload}`

`[arg]` = Optional

`<arg>` = Required

**Require Block**

Usage: `{require(<role,channel>):[response]}`

Aliases: `whitelist`

Payload: response, None

Parameter: role, channel

This block will attempt to convert the given parameter into a channel or role, using name or ID. If the user running the tag is not in the targeted channel or doesn't have the targeted role, the tag will stop processing and it will send the response if one is given. Multiple role or channel requirements can be given, and should be split by a ",".

**Blacklist Block**

Usage: `{blacklist(<role,channel>):[response]}`

Payload: response, None

Parameter: role, channel

Same usage and syntax as the require block, but instead of requiring the given channel or roles, it will block using the tag with those roles or in those channels.

**Redirect Block**

Usage: `{redirect(<"dm"|channel>)}`

Payload: None

Parameter: "dm", channel

Redirects the to either the given channel, or DMs the author if "dm" is passed as the parameter.

**Command Block**

Usage: `{command:<command>}`

Aliases: `c, com, command`

Payload: command

Parameter: None

The command block will run the given command as if the tag invoker had ran it. Only 3 can be used in a tag.


**Delete Block**

Usage: `{delete([bool])`

Payload: None

Parameter: bool, None

Delete blocks will delete the invocation message if the given parameter is true. If there is no parameter i.e. `{delete}` it will default to true.

**Args Block**

Usage: `{args([index]:[splitter])`

Payload: splitter, None

Parameter: index, None

An args block represents the arguments that follow a command's invocation name. If an index is provided, it will return the word at that position in the arguments list. If not it will return all arguments. If a splitter is provided, indexing will split using that character instead of the default " ".


**Author Block**

Aliases: `user`

Usage: `{author([attribute])`

Payload: None

Parameter: attribute, None

By default this will return the tag invoker's full username. Certain attributes can be passed to the payload to access more information about the author. These include:

```
id
name
nick
avatar
discriminator
created_at
joined_at
mention
bot
```


**Target Block**

Aliases: `member`

Usage: `{target([attribute])`

Payload: None

Parameter: attribute, None

The target block has the same usage and functionaliy as the author block, but it references the first person mentioned in the invoke message, if someone was mentioned.


**Channel Block**

Usage: `{channel([attribute])`

Payload: None

Parameter: attribute, None

By default this will return the tag's invoke channel name. Certain attributes can be passed to the payload to access more information about the channel. These include:

```
id
name
discriminator
created_at
nsfw
mention
topic
```


**Server Block**

Aliases: `guild`

Usage: `{server([attribute])`

Payload: None

Parameter: attribute, None

By default this will return the tag's invoke server name. Certain attributes can be passed to the payload to access more information about the server. These include:

```
id
name
nick
icon
discriminator
member_count
description
```

**Embed Block**

Usage: `{embed(<json>)}`

Payload: None

Parameter: json

Embed blocks will send an embed in the tag response.

**React Block**

Usage: `{react(<emoji,emoji>)}`

Payload: None

Parameter: emoji

The react block will react with up to 5 emoji to the tag response message. The given emoji can be custom or unicode emoji. Emojis can be split with ",".

**Reactu Block**

Usage: `{reactu(<emoji,emoji>)}`

Payload: None

Parameter: emoji

The react block will react with up to 5 emoji to the tag invocation message. The given emoji can be custom or unicode emoji. Emojis can be split with ",".