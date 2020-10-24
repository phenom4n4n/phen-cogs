# Tags [WIP]

Welcome to the incomplete TagScript documentation. This will explain the custom TagScript blocks. If a block you are looking for isn't here, then you should check if its in the base [TagScriptEngine docs](https://github.com/JonSnowbd/TagScript).

**Blocks:**

    - command
    
    - delete
    
    - args
    
    - author

    - target

    - channel

    -server

**Block Syntax:**

`{block(payload):parameter}`

`[arg]` = Optional

`<arg>` = Required


**Command Block**

Usage: `{command: <command>}`

Aliases: `c, com, command`

Payload: None

Parameter: command

The command block will run the given command as if the tag invoker had ran it. Only 3 can be used in a tag.


**Delete Block**

Usage: `{delete([bool])`

Payload: bool, None

Parameter: None

Delete blocks will delete the invocation message if the given payload is true. If there is no payload i.e. `{delete}` it will default to true.


**Args Block**

Usage: `{args([index])`

Payload: index, None

Parameter: None

An args block represents the arguments that follow a command's invocation name. If an index is provided, it will return the word at that position in the arguments list. Defaults to all arguments.


**Author Block**

Aliases: `user`

Usage: `{author([attribute])`

Payload: attribute, None

Parameter: None

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
```


**Target Block**

Aliases: `member`

Usage: `{target([attribute])`

Payload: attribute, None

Parameter: None

The target block has the same usage and functionaliy as the author block, but it references the first person mentioned in the invoke message, if someone was mentioned.


**Channel Block**

Usage: `{channel([attribute])`

Payload: attribute, None

Parameter: None

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

Payload: attribute, None

Parameter: None

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

