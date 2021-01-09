from .command import CommandBlock
from .delete import DeleteBlock
from .embed import EmbedBlock
from .silent import SilentBlock
from .require_blacklist import RequireBlock, BlacklistBlock
from .react import ReactBlock, ReactUBlock
from .redirect import RedirectBlock

stable_blocks = [
    CommandBlock(),
    DeleteBlock(),
    EmbedBlock(),
    SilentBlock(),
    RequireBlock(),
    BlacklistBlock(),
    ReactBlock(),
    RedirectBlock(),
    ReactUBlock(),
]
__all__ = (
    "CommandBlock",
    "DeleteBlock",
    "EmbedBlock",
    "SilentBlock",
    "RequireBlock",
    "BlacklistBlock",
    "ReactBlock",
    "RedirectBlock",
    "ReactUBlock",
)
