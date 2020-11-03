from .command import CommandBlock
from .delete import DeleteBlock
from .embed import EmbedBlock
from .silent import SilentBlock

stable_blocks = [CommandBlock(), DeleteBlock(), EmbedBlock(), SilentBlock()]
