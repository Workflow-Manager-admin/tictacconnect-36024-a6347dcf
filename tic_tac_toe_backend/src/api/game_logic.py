"""
Contains the encapsulated Tic Tac Toe game logic for move validation, board creation,
win/draw detection, and board manipulation. This is reused by the main FastAPI routes
to ensure a single source of correct gameplay logic for all state transitions.
"""

from typing import List, Optional, Any

class InvalidMove(Exception):
    """Raised when an invalid move is attempted in the game."""
    pass

class NotPlayersTurn(Exception):
    """Raised when a user attempts a move out of turn."""
    pass

class CellOccupied(Exception):
    """Raised if a move targets a non-empty cell."""
    pass

# PUBLIC_INTERFACE
def create_board_from_moves(moves: List[Any], user1_id: int, user2_id: int) -> List[List[Optional[int]]]:
    """
    Given a list of Move ORM objects or dicts, the two player IDs, return the 3x3 board
    as a list of lists, with entries being user1_id or user2_id or None.
    """
    board = [[None for _ in range(3)] for _ in range(3)]
    for m in moves:
        uid = getattr(m, "user_id", m.get("user_id", None))
        row = getattr(m, "row", m.get("row", None))
        col = getattr(m, "col", m.get("col", None))
        if row is not None and col is not None:
            board[row][col] = uid
    return board

# PUBLIC_INTERFACE
def validate_and_get_next_player(moves: List[Any], user1_id: int, user2_id: int, current_user_id: int) -> int:
    """
    Raises NotPlayersTurn if the move is out-of-turn.
    Returns the user_id of the player who should play next.
    """
    if user2_id is None:
        raise InvalidMove("Cannot make a move until opponent joins.")
    next_player = user1_id if len(moves) % 2 == 0 else user2_id
    if current_user_id != next_player:
        raise NotPlayersTurn("It's not your turn.")
    return next_player

# PUBLIC_INTERFACE
def is_cell_empty(board: List[List[Optional[int]]], row: int, col: int) -> bool:
    """
    Returns True if board[row][col] is empty. Raises CellOccupied otherwise.
    """
    if board[row][col] is not None:
        raise CellOccupied("Cell already taken.")
    return True

# PUBLIC_INTERFACE
def check_winner(board: List[List[Optional[int]]], user1_id: int, user2_id: int) -> Optional[int]:
    """
    Checks if either player has won. Returns the user_id of the winner, or None.
    """
    for marker in [user1_id, user2_id]:
        # Rows
        for i in range(3):
            if all(board[i][j] == marker for j in range(3)):
                return marker
        # Columns
        for j in range(3):
            if all(board[i][j] == marker for i in range(3)):
                return marker
        # Diagonals
        if all(board[i][i] == marker for i in range(3)):
            return marker
        if all(board[i][2 - i] == marker for i in range(3)):
            return marker
    return None

# PUBLIC_INTERFACE
def is_board_full(moves: List[Any]) -> bool:
    """
    Returns True if there are 9 moves, meaning the board is full (possibly a draw).
    """
    return len(moves) >= 9

# PUBLIC_INTERFACE
def game_drawn(board: List[List[Optional[int]]]) -> bool:
    """
    Returns True if the board is full and no winner is present.
    """
    for row in board:
        for cell in row:
            if cell is None:
                return False
    return True

