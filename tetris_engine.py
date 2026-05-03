"""
tetris_engine.py
----------------
Core game logic cho Tetris. Hoàn toàn độc lập, không phụ thuộc framework.
"""

import random
import copy
from enum import Enum
from typing import Optional


# ─────────────────────────────────────────────
# Hằng số
# ─────────────────────────────────────────────

BOARD_COLS = 10
BOARD_ROWS = 20

# Điểm thưởng khi xóa dòng (theo chuẩn Tetris Guideline)
LINE_SCORE = {1: 100, 2: 300, 3: 500, 4: 800}

# Tốc độ rơi theo level (giây / ô)
LEVEL_SPEED = {
    1: 1.000, 2: 0.793, 3: 0.618, 4: 0.473,
    5: 0.355, 6: 0.262, 7: 0.190, 8: 0.135,
    9: 0.094, 10: 0.064,
}

# ─────────────────────────────────────────────
# Định nghĩa Tetromino
# ─────────────────────────────────────────────

class TetrominoType(str, Enum):
    I = "I"
    O = "O"
    T = "T"
    S = "S"
    Z = "Z"
    J = "J"
    L = "L"


# Mỗi piece có 4 trạng thái xoay (0°, 90°, 180°, 270°)
# Mỗi trạng thái là list các (row, col) offset tính từ pivot
TETROMINOES: dict[str, list[list[tuple[int, int]]]] = {
    "I": [
        [(0,0),(0,1),(0,2),(0,3)],
        [(0,2),(1,2),(2,2),(3,2)],
        [(2,0),(2,1),(2,2),(2,3)],
        [(0,1),(1,1),(2,1),(3,1)],
    ],
    "O": [
        [(0,0),(0,1),(1,0),(1,1)],
        [(0,0),(0,1),(1,0),(1,1)],
        [(0,0),(0,1),(1,0),(1,1)],
        [(0,0),(0,1),(1,0),(1,1)],
    ],
    "T": [
        [(0,1),(1,0),(1,1),(1,2)],
        [(0,1),(1,1),(1,2),(2,1)],
        [(1,0),(1,1),(1,2),(2,1)],
        [(0,1),(1,0),(1,1),(2,1)],
    ],
    "S": [
        [(0,1),(0,2),(1,0),(1,1)],
        [(0,1),(1,1),(1,2),(2,2)],
        [(1,1),(1,2),(2,0),(2,1)],
        [(0,0),(1,0),(1,1),(2,1)],
    ],
    "Z": [
        [(0,0),(0,1),(1,1),(1,2)],
        [(0,2),(1,1),(1,2),(2,1)],
        [(1,0),(1,1),(2,1),(2,2)],
        [(0,1),(1,0),(1,1),(2,0)],
    ],
    "J": [
        [(0,0),(1,0),(1,1),(1,2)],
        [(0,1),(0,2),(1,1),(2,1)],
        [(1,0),(1,1),(1,2),(2,2)],
        [(0,1),(1,1),(2,0),(2,1)],
    ],
    "L": [
        [(0,2),(1,0),(1,1),(1,2)],
        [(0,1),(1,1),(2,1),(2,2)],
        [(1,0),(1,1),(1,2),(2,0)],
        [(0,0),(0,1),(1,1),(2,1)],
    ],
}

# Màu sắc chuẩn Tetris Guideline (hex)
TETROMINO_COLORS: dict[str, str] = {
    "I": "#00F0F0",
    "O": "#F0F000",
    "T": "#A000F0",
    "S": "#00F000",
    "Z": "#F00000",
    "J": "#0000F0",
    "L": "#F0A000",
}


# ─────────────────────────────────────────────
# Class Piece — mảnh đang rơi
# ─────────────────────────────────────────────

class Piece:
    def __init__(self, type_: str, row: int = 0, col: int = 3, rotation: int = 0):
        self.type = type_
        self.row = row
        self.col = col
        self.rotation = rotation

    @property
    def cells(self) -> list[tuple[int, int]]:
        """Trả về tọa độ tuyệt đối các ô của mảnh trên bảng."""
        offsets = TETROMINOES[self.type][self.rotation]
        return [(self.row + dr, self.col + dc) for dr, dc in offsets]

    def clone(self) -> "Piece":
        return Piece(self.type, self.row, self.col, self.rotation)

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "row": self.row,
            "col": self.col,
            "rotation": self.rotation,
            "cells": self.cells,
            "color": TETROMINO_COLORS[self.type],
        }


# ─────────────────────────────────────────────
# Class TetrisEngine — trái tim game
# ─────────────────────────────────────────────

class TetrisEngine:
    """
    Quản lý toàn bộ trạng thái game Tetris.

    Cách dùng:
        engine = TetrisEngine()
        engine.action("move_left")
        engine.tick()          # gọi mỗi frame / interval
        state = engine.get_state()
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self._bag: list[str] = []          # 7-bag randomizer
        self.board: list[list[Optional[str]]] = self._empty_board()
        self.current: Piece = self._spawn_piece()
        self.next_piece: str = self._draw_piece_type()
        self.held: Optional[str] = None
        self.hold_used: bool = False       # chỉ hold 1 lần / mảnh
        self.score: int = 0
        self.lines: int = 0
        self.level: int = 1
        self.game_over: bool = False
        self.combo: int = 0                # combo counter
        self.last_action_clear: bool = False

    # ── Bảng ──────────────────────────────────

    @staticmethod
    def _empty_board() -> list[list[Optional[str]]]:
        return [[None] * BOARD_COLS for _ in range(BOARD_ROWS)]

    def _board_copy(self) -> list[list[Optional[str]]]:
        return [row[:] for row in self.board]

    # ── Túi 7 mảnh (7-bag randomizer) ─────────

    def _refill_bag(self):
        types = list(TETROMINOES.keys())
        self.rng.shuffle(types)
        self._bag.extend(types)

    def _draw_piece_type(self) -> str:
        if not self._bag:
            self._refill_bag()
        return self._bag.pop(0)

    def _spawn_piece(self) -> Piece:
        t = self._draw_piece_type()
        return Piece(t, row=0, col=3, rotation=0)

    # ── Kiểm tra va chạm ──────────────────────

    def _is_valid(self, piece: Piece) -> bool:
        for r, c in piece.cells:
            if r < 0 or r >= BOARD_ROWS:
                return False
            if c < 0 or c >= BOARD_COLS:
                return False
            if self.board[r][c] is not None:
                return False
        return True

    # ── Ghost piece (bóng mờ) ─────────────────

    def _ghost(self) -> Piece:
        ghost = self.current.clone()
        while True:
            ghost.row += 1
            if not self._is_valid(ghost):
                ghost.row -= 1
                break
        return ghost

    # ── Lock piece vào bảng ───────────────────

    def _lock(self):
        for r, c in self.current.cells:
            if r < 0:
                self.game_over = True
                return
            self.board[r][c] = self.current.type

        cleared = self._clear_lines()
        self._update_score(cleared)

        # Sinh mảnh mới
        self.current = Piece(self.next_piece, row=0, col=3, rotation=0)
        self.next_piece = self._draw_piece_type()
        self.hold_used = False

        if not self._is_valid(self.current):
            self.game_over = True

    # ── Xóa dòng ──────────────────────────────

    def _clear_lines(self) -> int:
        new_board = [row for row in self.board if any(c is None for c in row)]
        cleared = BOARD_ROWS - len(new_board)
        for _ in range(cleared):
            new_board.insert(0, [None] * BOARD_COLS)
        self.board = new_board
        return cleared

    # ── Tính điểm ─────────────────────────────

    def _update_score(self, cleared: int):
        if cleared:
            self.combo += 1
            base = LINE_SCORE.get(cleared, 0) * self.level
            combo_bonus = 50 * self.combo * self.level
            self.score += base + combo_bonus
            self.lines += cleared
            self.level = min(10, 1 + self.lines // 10)
            self.last_action_clear = True
        else:
            self.combo = 0
            self.last_action_clear = False

    # ── API hành động ─────────────────────────

    ACTIONS = {"move_left", "move_right", "move_down",
               "rotate_cw", "rotate_ccw", "hard_drop", "hold"}

    def action(self, name: str) -> dict:
        """
        Thực hiện hành động của người chơi.
        Trả về {"ok": bool, "locked": bool, "game_over": bool}
        """
        if self.game_over:
            return {"ok": False, "locked": False, "game_over": True}
        if name not in self.ACTIONS:
            return {"ok": False, "locked": False, "game_over": False, "error": f"Unknown action: {name}"}

        locked = False

        if name == "move_left":
            self._try_move(0, -1)

        elif name == "move_right":
            self._try_move(0, 1)

        elif name == "move_down":
            if not self._try_move(1, 0):
                self._lock()
                locked = True

        elif name == "rotate_cw":
            self._try_rotate(1)

        elif name == "rotate_ccw":
            self._try_rotate(-1)

        elif name == "hard_drop":
            ghost = self._ghost()
            drop_distance = ghost.row - self.current.row
            self.score += drop_distance * 2
            self.current = ghost
            self._lock()
            locked = True

        elif name == "hold":
            self._do_hold()

        return {"ok": True, "locked": locked, "game_over": self.game_over}

    def _try_move(self, dr: int, dc: int) -> bool:
        moved = self.current.clone()
        moved.row += dr
        moved.col += dc
        if self._is_valid(moved):
            self.current = moved
            return True
        return False

    def _try_rotate(self, direction: int):
        """Xoay với Wall Kick đơn giản."""
        rotated = self.current.clone()
        rotated.rotation = (rotated.rotation + direction) % 4

        kicks = [(0,0), (0,-1), (0,1), (0,-2), (0,2), (-1,0)]
        for dr, dc in kicks:
            rotated.row = self.current.row + dr
            rotated.col = self.current.col + dc
            if self._is_valid(rotated):
                self.current = rotated
                return

    def _do_hold(self):
        if self.hold_used:
            return
        self.hold_used = True
        if self.held is None:
            self.held = self.current.type
            self.current = Piece(self.next_piece, row=0, col=3, rotation=0)
            self.next_piece = self._draw_piece_type()
        else:
            self.held, self.current = (
                self.current.type,
                Piece(self.held, row=0, col=3, rotation=0),
            )

    # ── Tick (auto-fall) ──────────────────────

    def tick(self) -> dict:
        """Gọi định kỳ để mảnh tự rơi xuống."""
        return self.action("move_down")

    # ── Xuất trạng thái ───────────────────────

    def get_state(self) -> dict:
        ghost = self._ghost() if not self.game_over else None
        return {
            "board": self._board_with_colors(),
            "current": self.current.to_dict(),
            "next": {
                "type": self.next_piece,
                "color": TETROMINO_COLORS[self.next_piece],
                "cells": TETROMINOES[self.next_piece][0],
            },
            "ghost": ghost.to_dict() if ghost else None,
            "held": {
                "type": self.held,
                "color": TETROMINO_COLORS[self.held],
                "cells": TETROMINOES[self.held][0],
            } if self.held else None,
            "score": self.score,
            "lines": self.lines,
            "level": self.level,
            "combo": self.combo,
            "game_over": self.game_over,
            "fall_speed": LEVEL_SPEED.get(self.level, 0.064),
        }

    def _board_with_colors(self) -> list[list[Optional[str]]]:
        """Trả về board với giá trị là màu hex (hoặc None)."""
        result = []
        for row in self.board:
            result.append([
                TETROMINO_COLORS[cell] if cell else None
                for cell in row
            ])
        return result