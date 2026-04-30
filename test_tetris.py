"""
test_tetris.py
--------------
Unit tests cho TetrisEngine — chạy bằng pytest hoặc python test_tetris.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from tetris_engine import TetrisEngine, BOARD_COLS, BOARD_ROWS, TETROMINO_COLORS


def make_engine(seed=42) -> TetrisEngine:
    return TetrisEngine(seed=seed)


# ── Test khởi tạo ─────────────────────────────────────────────────────────

def test_initial_board_empty():
    engine = make_engine()
    for row in engine.board:
        assert all(c is None for c in row), "Board khởi tạo phải trống"
    print("✅ test_initial_board_empty")


def test_initial_state_fields():
    engine = make_engine()
    state = engine.get_state()
    assert state["score"] == 0
    assert state["lines"] == 0
    assert state["level"] == 1
    assert state["game_over"] is False
    assert state["current"] is not None
    assert state["next"] is not None
    print("✅ test_initial_state_fields")


# ── Test di chuyển ────────────────────────────────────────────────────────

def test_move_left_changes_col():
    engine = make_engine()
    original_col = engine.current.col
    engine.action("move_left")
    assert engine.current.col == original_col - 1
    print("✅ test_move_left_changes_col")


def test_move_right_changes_col():
    engine = make_engine()
    original_col = engine.current.col
    engine.action("move_right")
    assert engine.current.col == original_col + 1
    print("✅ test_move_right_changes_col")


def test_cannot_move_left_beyond_wall():
    engine = make_engine()
    for _ in range(20):  # Di chuyển nhiều lần hơn chiều rộng board
        engine.action("move_left")
    for r, c in engine.current.cells:
        assert c >= 0, "Không được vượt qua tường trái"
    print("✅ test_cannot_move_left_beyond_wall")


def test_cannot_move_right_beyond_wall():
    engine = make_engine()
    for _ in range(20):
        engine.action("move_right")
    for r, c in engine.current.cells:
        assert c < BOARD_COLS, "Không được vượt qua tường phải"
    print("✅ test_cannot_move_right_beyond_wall")


# ── Test xoay ─────────────────────────────────────────────────────────────

def test_rotate_cw_changes_rotation():
    engine = make_engine()
    original_rot = engine.current.rotation
    engine.action("rotate_cw")
    assert engine.current.rotation == (original_rot + 1) % 4
    print("✅ test_rotate_cw_changes_rotation")


def test_rotate_ccw_changes_rotation():
    engine = make_engine()
    original_rot = engine.current.rotation
    engine.action("rotate_ccw")
    assert engine.current.rotation == (original_rot - 1) % 4
    print("✅ test_rotate_ccw_changes_rotation")


def test_rotate_4_times_returns_original():
    engine = make_engine()
    original_rot = engine.current.rotation
    for _ in range(4):
        engine.action("rotate_cw")
    assert engine.current.rotation == original_rot
    print("✅ test_rotate_4_times_returns_original")


# ── Test hard drop ────────────────────────────────────────────────────────

def test_hard_drop_locks_piece():
    engine = make_engine()
    result = engine.action("hard_drop")
    assert result["locked"] is True
    # Sau khi lock, board phải có ít nhất 1 ô được tô
    total_filled = sum(1 for row in engine.board for c in row if c is not None)
    assert total_filled > 0
    print("✅ test_hard_drop_locks_piece")


def test_hard_drop_scores_bonus():
    engine = make_engine()
    engine.action("hard_drop")
    # Hard drop từ row 0 xuống phải cho điểm
    assert engine.score > 0
    print("✅ test_hard_drop_scores_bonus")


# ── Test xóa dòng ─────────────────────────────────────────────────────────

def test_clear_single_line():
    """Điền đầy 1 dòng, gọi _clear_lines() trực tiếp, kiểm tra board."""
    engine = make_engine()
    # Điền đầy dòng cuối cùng
    for c in range(BOARD_COLS):
        engine.board[BOARD_ROWS - 1][c] = "I"

    cleared = engine._clear_lines()
    assert cleared == 1, f"Phải xóa được 1 dòng, nhưng xóa {cleared}"
    # Dòng cuối sau khi xóa phải trống
    assert all(c is None for c in engine.board[BOARD_ROWS - 1])
    print("✅ test_clear_single_line")


# ── Test hold ────────────────────────────────────────────────────────────

def test_hold_swaps_piece():
    engine = make_engine()
    current_type = engine.current.type
    engine.action("hold")
    assert engine.held == current_type
    assert engine.current.type != current_type or engine.held is not None
    print("✅ test_hold_swaps_piece")


def test_hold_only_once_per_piece():
    engine = make_engine()
    engine.action("hold")
    type_after_first_hold = engine.current.type
    engine.action("hold")  # Lần 2 không được phép
    assert engine.current.type == type_after_first_hold
    print("✅ test_hold_only_once_per_piece")


# ── Test ghost piece ──────────────────────────────────────────────────────

def test_ghost_below_current():
    engine = make_engine()
    ghost = engine._ghost()
    assert ghost.row >= engine.current.row
    print("✅ test_ghost_below_current")


def test_ghost_in_state():
    engine = make_engine()
    state = engine.get_state()
    assert state["ghost"] is not None
    assert "cells" in state["ghost"]
    print("✅ test_ghost_in_state")


# ── Test level và tốc độ ──────────────────────────────────────────────────

def test_level_increases_with_lines():
    engine = make_engine()
    engine.lines = 10
    engine._update_score(1)
    assert engine.level >= 2
    print("✅ test_level_increases_with_lines")


def test_fall_speed_in_state():
    engine = make_engine()
    state = engine.get_state()
    assert "fall_speed" in state
    assert 0 < state["fall_speed"] <= 1.0
    print("✅ test_fall_speed_in_state")


# ── Test game over ────────────────────────────────────────────────────────

def test_action_rejected_when_game_over():
    engine = make_engine()
    engine.game_over = True
    result = engine.action("move_left")
    assert result["ok"] is False
    print("✅ test_action_rejected_when_game_over")


def test_unknown_action_returns_error():
    engine = make_engine()
    result = engine.action("fly_up")
    assert result["ok"] is False
    assert "error" in result
    print("✅ test_unknown_action_returns_error")


# ── Chạy tất cả tests ─────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_initial_board_empty,
        test_initial_state_fields,
        test_move_left_changes_col,
        test_move_right_changes_col,
        test_cannot_move_left_beyond_wall,
        test_cannot_move_right_beyond_wall,
        test_rotate_cw_changes_rotation,
        test_rotate_ccw_changes_rotation,
        test_rotate_4_times_returns_original,
        test_hard_drop_locks_piece,
        test_hard_drop_scores_bonus,
        test_clear_single_line,
        test_hold_swaps_piece,
        test_hold_only_once_per_piece,
        test_ghost_below_current,
        test_ghost_in_state,
        test_level_increases_with_lines,
        test_fall_speed_in_state,
        test_action_rejected_when_game_over,
        test_unknown_action_returns_error,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {test.__name__}: EXCEPTION — {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"  Kết quả: {passed}/{len(tests)} tests passed")
    if failed:
        print(f"  ❌ {failed} tests FAILED")
        sys.exit(1)
    else:
        print("  🎉 Tất cả tests đều pass!")
