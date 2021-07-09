==================
Example Slash Tags
==================

The following examples show the capabilities of slash tags.

Command Execution Example
-------------------------

This slash tag adds a ``/ban`` command that can be used to ban users.

Arguments:

+------------+-------------------------+------------+----------+
| Name       | Description             | Type       | Required |
+============+=========================+============+==========+
| ``victim`` | A member to ban.        | ``member`` | True     |
+------------+-------------------------+------------+----------+
| ``reason`` | The reason for the ban. | ``string`` | False    |
+------------+-------------------------+------------+----------+

::

    [p]slashtag add ban {c:ban {victim(id)} {reason}}
