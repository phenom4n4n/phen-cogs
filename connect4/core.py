"""
MIT License

Copyright (c) 2020-present phenom4n4n

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from itertools import chain, groupby
from typing import Union

import discord


class Board(list):
    __slots__ = frozenset({"width", "height"})

    def __init__(self, width, height, player1_name=None, player2_name=None):
        self.width = width
        self.height = height
        for _ in range(width):
            self.append([0] * height)

    def __getitem__(self, pos: Union[int, tuple]):
        if isinstance(pos, int):
            return super().__getitem__(pos)
        elif isinstance(pos, tuple):
            x, y = pos
            return super().__getitem__(x)[y]
        else:
            raise TypeError("pos must be an int or tuple")

    def __setitem__(self, pos: Union[int, tuple], new_value):
        x, y = self._xy(pos)

        if self[x, y] != 0:
            raise IndexError("there's already a move at that position")

        # basically self[x][y] = new_value
        # super().__getitem__(x).__setitem__(y, new_value)
        self[x][y] = new_value

    def _xy(self, pos):
        if isinstance(pos, tuple):
            return pos[0], pos[1]
        elif isinstance(pos, int):
            x = pos
            return x, self._y(x)
        else:
            raise TypeError("pos must be an int or tuple")

    def _y(self, x):
        """find the lowest empty row for column x"""
        # start from the bottom and work up
        for y in range(self.height - 1, -1, -1):
            if self[x, y] == 0:
                return y
        raise ValueError("that column is full")

    def _position_check(self, x: int, y: int) -> bool:
        """Checks if the given position is in the board"""
        return x >= 0 and y >= 0 and x < self.width and y < self.height

    def _pos_diagonals(self):
        """Get positive diagonals, going from bottom-left to top-right."""
        for y in range(self.width + self.height - 1):
            diagonal = [(x, y - x) for x in range(self.width)]
            yield [self[i, j] for i, j in diagonal if self._position_check(i, j)]

    def _neg_diagonals(self):
        """Get negative diagonals, going from top-left to bottom-right."""
        for y in range(self.width + self.height - 1):
            diagonal = [(x, y - self.width + x + 1) for x in range(self.width)]
            yield [self[i, j] for i, j in diagonal if self._position_check(i, j)]

    def _full(self):
        """is there a move in every position?"""

        return all(self[x, 0] != 0 for x in range(self.width))


class Connect4Game:
    FORFEIT = -2
    TIE = -1
    NO_WINNER = 0

    PIECES = "\N{medium white circle}" "\N{large red circle}" "\N{large blue circle}"

    __slots__ = (
        "player1",
        "player2",
        "players",
        "board",
        "turn_count",
        "_whomst_forfeited",
        "player_ids",
    )

    def __init__(self, player1: discord.Member, player2: discord.Member):
        self.player1 = player1
        self.player2 = player2
        self.players = (player1, player2)
        self.player_ids = {p.id for p in self.players}

        self.board = Board(7, 6)
        self.turn_count = 0
        self._whomst_forfeited = 0

    def move(self, column):
        self.board[column] = self.whomst_turn()
        self.turn_count += 1

    def forfeit(self):
        """forfeit the game as the current player"""
        self._whomst_forfeited = self.whomst_turn_name()

    def _get_forfeit_status(self):
        if self._whomst_forfeited:
            status = "{} won ({} forfeited)\n"

            return status.format(self.other_player_name(), self.whomst_turn_name())

        raise ValueError("nobody has forfeited")

    def __str__(self):
        win_status = self.whomst_won()
        status = self._get_status()
        instructions = ""

        if win_status == self.NO_WINNER:
            instructions = self._get_instructions()
        elif win_status == self.FORFEIT:
            status = self._get_forfeit_status()

        return (
            status
            + instructions
            + "\n".join(self._format_row(y) for y in range(self.board.height))
        )

    def _get_status(self):
        win_status = self.whomst_won()

        if win_status == self.NO_WINNER:
            status = self.whomst_turn_name() + "'s turn " + self.PIECES[self.whomst_turn()]
        elif win_status == self.TIE:
            status = "It's a tie!"
        elif win_status == self.FORFEIT:
            status = self._get_forfeit_status()
        else:
            status = self._get_player_name(win_status) + " won!"
        return status + "\n"

    def _get_instructions(self):
        instructions = "".join(
            str(i) + "\N{combining enclosing keycap}" for i in range(1, self.board.width + 1)
        )

        return instructions + "\n"

    def _format_row(self, y):
        return "".join(self[x, y] for x in range(self.board.width))

    def __getitem__(self, pos):
        x, y = pos
        return self.PIECES[self.board[x, y]]

    def whomst_won(self) -> int:
        """Get the winner on the current board.
        If there's no winner yet, return Connect4Game.NO_WINNER.
        If it's a tie, return Connect4Game.TIE"""

        lines = (
            self.board,  # columns
            zip(*self.board),  # rows (zip picks the nth item from each column)
            self.board._pos_diagonals(),  # positive diagonals
            self.board._neg_diagonals(),  # negative diagonals
        )

        if self._whomst_forfeited:
            return self.FORFEIT

        for line in chain(*lines):
            for player, group in groupby(line):
                if player != 0 and len(list(group)) >= 4:
                    return player

        if self.board._full():
            return self.TIE
        else:
            return self.NO_WINNER

    def other_player_name(self):
        self.turn_count += 1
        other_player_name = self.whomst_turn_name()
        self.turn_count -= 1
        return other_player_name

    def whomst_turn_name(self):
        return self._get_player_name(self.whomst_turn())

    def whomst_turn(self) -> int:
        return self.turn_count % 2 + 1

    def _get_player_name(self, player_number):
        player_number -= 1  # these lists are 0-indexed but the players aren't
        # return self.players[player_number].display_name
        return self.players[player_number].mention

    @property
    def current_player(self) -> discord.Member:
        player_number = self.whomst_turn() - 1
        return self.players[player_number]
