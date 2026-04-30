"""
app.py
------
Flask REST API backend cho game Tetris.

Chạy:
    pip install flask flask-cors
    python app.py

API:
    POST /api/game/new          — Tạo game mới
    GET  /api/game/<id>         — Lấy trạng thái game
    POST /api/game/<id>/action  — Gửi hành động người chơi
    POST /api/game/<id>/tick    — Trigger auto-fall (gọi từ frontend timer)
    POST /api/game/<id>/restart — Khởi động lại game
    GET  /api/game/<id>/scores  — Top 10 điểm cao (trong session)
    GET  /api/info              — Thông tin API
"""

import uuid
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from tetris_engine import TetrisEngine

app = Flask(__name__)
CORS(app)  # Cho phép frontend ở domain khác kết nối

# ── Lưu trữ session game trong RAM ────────────────────────────────────────
# Key: game_id (str), Value: {"engine": TetrisEngine, "created_at": float, "player": str}
GAMES: dict[str, dict] = {}
LEADERBOARD: list[dict] = []    # Top scores toàn session
MAX_GAMES = 100                  # Giới hạn để tránh tràn bộ nhớ


# ── Helper ────────────────────────────────────────────────────────────────

def get_game_or_404(game_id: str):
    """Trả về game hoặc abort 404."""
    game = GAMES.get(game_id)
    if not game:
        return None, jsonify({"error": "Game not found", "game_id": game_id}), 404
    return game, None, None


def cleanup_old_games():
    """Xóa các game cũ nếu vượt giới hạn (FIFO)."""
    if len(GAMES) > MAX_GAMES:
        oldest_id = next(iter(GAMES))
        del GAMES[oldest_id]


# ── Routes ────────────────────────────────────────────────────────────────

@app.route("/api/info", methods=["GET"])
def api_info():
    """Thông tin tổng quát về API."""
    return jsonify({
        "name": "Tetris Backend API",
        "version": "1.0.0",
        "description": "REST API cho game Tetris — Software Engineering Assignment",
        "active_games": len(GAMES),
        "endpoints": {
            "POST /api/game/new": "Tạo game mới",
            "GET  /api/game/<id>": "Lấy trạng thái game",
            "POST /api/game/<id>/action": "Gửi hành động: move_left | move_right | move_down | rotate_cw | rotate_ccw | hard_drop | hold",
            "POST /api/game/<id>/tick": "Auto-fall tick",
            "POST /api/game/<id>/restart": "Khởi động lại",
            "GET  /api/leaderboard": "Bảng xếp hạng điểm cao",
        },
    })


@app.route("/api/game/new", methods=["POST"])
def new_game():
    """
    Tạo game mới.

    Body (JSON, tuỳ chọn):
        { "player": "Tên người chơi", "seed": 42 }

    Trả về:
        { "game_id": "...", "state": {...} }
    """
    cleanup_old_games()

    body = request.get_json(silent=True) or {}
    player = body.get("player", "Anonymous")
    seed = body.get("seed", None)

    game_id = str(uuid.uuid4())
    engine = TetrisEngine(seed=seed)

    GAMES[game_id] = {
        "engine": engine,
        "player": player,
        "created_at": time.time(),
        "last_action": time.time(),
    }

    return jsonify({
        "game_id": game_id,
        "player": player,
        "state": engine.get_state(),
    }), 201


@app.route("/api/game/<game_id>", methods=["GET"])
def get_state(game_id: str):
    """
    Lấy trạng thái hiện tại của game.

    Trả về toàn bộ game state bao gồm:
    - board: 20×10 grid (màu hex hoặc null)
    - current: mảnh đang rơi
    - next: mảnh kế tiếp
    - ghost: bóng mờ (vị trí mảnh sẽ rơi xuống)
    - held: mảnh đang giữ
    - score, lines, level, combo
    - game_over: bool
    - fall_speed: giây/ô theo level hiện tại
    """
    game, err, status = get_game_or_404(game_id)
    if err:
        return err, status

    return jsonify({
        "game_id": game_id,
        "player": game["player"],
        "state": game["engine"].get_state(),
    })


@app.route("/api/game/<game_id>/action", methods=["POST"])
def player_action(game_id: str):
    """
    Gửi hành động của người chơi.

    Body (JSON, bắt buộc):
        { "action": "move_left" }

    Các action hợp lệ:
        move_left   — Di chuyển trái
        move_right  — Di chuyển phải
        move_down   — Di chuyển xuống 1 ô (soft drop)
        rotate_cw   — Xoay theo chiều kim đồng hồ
        rotate_ccw  — Xoay ngược chiều kim đồng hồ
        hard_drop   — Thả thẳng xuống (tính điểm bonus)
        hold        — Giữ mảnh hiện tại

    Trả về:
        { "result": {...}, "state": {...} }
    """
    game, err, status = get_game_or_404(game_id)
    if err:
        return err, status

    body = request.get_json(silent=True) or {}
    action = body.get("action", "").strip()

    if not action:
        return jsonify({"error": "Missing 'action' field in request body"}), 400

    engine: TetrisEngine = game["engine"]
    result = engine.action(action)
    game["last_action"] = time.time()

    # Nếu game kết thúc, lưu vào leaderboard
    if result.get("game_over") and engine.score > 0:
        _save_score(game_id, game["player"], engine.score, engine.lines, engine.level)

    return jsonify({
        "game_id": game_id,
        "action": action,
        "result": result,
        "state": engine.get_state(),
    })


@app.route("/api/game/<game_id>/tick", methods=["POST"])
def tick(game_id: str):
    """
    Trigger auto-fall — frontend gọi theo interval dựa trên fall_speed.

    Frontend nên đọc `state.fall_speed` (giây) và gọi endpoint này
    theo đúng khoảng thời gian đó.

    Trả về:
        { "result": {...}, "state": {...} }
    """
    game, err, status = get_game_or_404(game_id)
    if err:
        return err, status

    engine: TetrisEngine = game["engine"]
    result = engine.tick()
    game["last_action"] = time.time()

    if result.get("game_over") and engine.score > 0:
        _save_score(game_id, game["player"], engine.score, engine.lines, engine.level)

    return jsonify({
        "game_id": game_id,
        "result": result,
        "state": engine.get_state(),
    })


@app.route("/api/game/<game_id>/restart", methods=["POST"])
def restart_game(game_id: str):
    """Khởi động lại game, giữ nguyên player name."""
    game, err, status = get_game_or_404(game_id)
    if err:
        return err, status

    engine = TetrisEngine()
    GAMES[game_id]["engine"] = engine
    GAMES[game_id]["created_at"] = time.time()
    GAMES[game_id]["last_action"] = time.time()

    return jsonify({
        "game_id": game_id,
        "player": game["player"],
        "message": "Game restarted",
        "state": engine.get_state(),
    })


@app.route("/api/leaderboard", methods=["GET"])
def leaderboard():
    """Top 10 điểm cao trong session hiện tại."""
    top10 = sorted(LEADERBOARD, key=lambda x: x["score"], reverse=True)[:10]
    return jsonify({"leaderboard": top10, "total_entries": len(LEADERBOARD)})


# ── Internal helpers ───────────────────────────────────────────────────────

def _save_score(game_id: str, player: str, score: int, lines: int, level: int):
    LEADERBOARD.append({
        "game_id": game_id,
        "player": player,
        "score": score,
        "lines": lines,
        "level": level,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    })


# ── Error handlers ────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Route not found"}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error", "detail": str(e)}), 500


# ── Entrypoint ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  🎮  Tetris Backend API  —  http://localhost:22081")
    print("=" * 55)
    print("  GET  /api/info           — Xem tất cả endpoints")
    print("  POST /api/game/new       — Bắt đầu game mới")
    print("=" * 55)
    app.run(host="0.0.0.0", port=22081, debug=True)
