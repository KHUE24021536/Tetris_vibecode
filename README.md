# 🎮 Tetris — NoBug Stars Edition

Game Tetris desktop viết bằng **Python + Pygame**.  
Kiến trúc tách biệt rõ ràng: engine logic độc lập hoàn toàn với phần render.

---

## Cấu trúc dự án

```
Tetris_vibecode/
├── tetris_engine.py   # Core game logic (không phụ thuộc bất kỳ framework nào)
├── main.py            # Giao diện Pygame — render, input, hiệu ứng
├── test_tetris.py     # 20 unit tests cho engine
└── README.md
```

---

## Cài đặt & Chạy

```bash
pip install pygame
python main.py
```

Chạy tests:
```bash
python test_tetris.py
# hoặc
pytest test_tetris.py -v
```

---

## Điều khiển

| Phím          | Hành động                          |
|---------------|------------------------------------|
| `← →`         | Di chuyển trái / phải              |
| `↑`           | Xoay theo chiều kim đồng hồ        |
| `Z`           | Xoay ngược chiều kim đồng hồ       |
| `↓`           | Soft drop (rơi chậm)               |
| `Space`       | Hard drop (thả thẳng xuống)        |
| `C`           | Hold — giữ mảnh hiện tại           |
| `Enter`       | Bắt đầu / Restart                  |

---

## Tính năng

**Engine (`tetris_engine.py`)**
- 7 loại Tetromino chuẩn Tetris Guideline (I, O, T, S, Z, J, L)
- 7-bag randomizer — phân phối mảnh công bằng
- Ghost piece — bóng mờ hiển thị vị trí rơi
- Hold piece — chỉ được hold 1 lần mỗi mảnh
- Hard drop với điểm bonus (`distance × 2`)
- Xóa 1–4 dòng cùng lúc với điểm thưởng theo chuẩn guideline
- Combo bonus khi xóa dòng liên tiếp
- 10 cấp độ, tốc độ tăng dần theo số dòng đã xóa
- Wall kick đơn giản khi xoay gần tường

**Giao diện (`main.py`)**
- Cửa sổ 640×700, board 10×20 ô (mỗi ô 30px)
- Theme Dark Luxury — nền đen sâu, viền phát sáng
- 80 ngôi sao rơi nền động
- Particle explosion khi xóa dòng
- Viền board nhấp nháy theo nhịp thở
- Panel HOLD (trái) và NEXT + STATS (phải) với glow effect
- Thanh tiến độ level và chỉ số tốc độ rơi hiện tại
- COMBO đổi màu đỏ khi đạt ×2 trở lên
- Game Over overlay với điểm cuối, số dòng, cấp độ

---

## Scoring

| Sự kiện             | Điểm                                      |
|---------------------|-------------------------------------------|
| Xóa 1 dòng         | `100 × level`                             |
| Xóa 2 dòng         | `300 × level`                             |
| Xóa 3 dòng         | `500 × level`                             |
| Xóa 4 dòng (Tetris)| `800 × level`                             |
| Combo bonus         | `50 × combo_count × level` (cộng dồn)    |
| Hard drop           | `2 điểm × số ô rơi`                      |

---

## Tốc độ theo Level

| Level | Giây/ô | Level | Giây/ô |
|-------|--------|-------|--------|
| 1     | 1.000  | 6     | 0.262  |
| 2     | 0.793  | 7     | 0.190  |
| 3     | 0.618  | 8     | 0.135  |
| 4     | 0.473  | 9     | 0.094  |
| 5     | 0.355  | 10    | 0.064  |

Level tăng mỗi 10 dòng xóa được, tối đa level 10.

---

## Kiến trúc

```
┌─────────────────────────────┐
│         main.py             │
│  Pygame render + Input      │
│  Particle / Star effects    │
│  60 FPS game loop           │
└──────────────┬──────────────┘
               │ import & gọi
┌──────────────▼──────────────┐
│      tetris_engine.py       │
│  TetrisEngine — game state  │
│  Piece — mảnh đang rơi      │
│  7-bag / scoring / physics  │
└─────────────────────────────┘
```

`TetrisEngine` hoàn toàn độc lập với Pygame — có thể tái sử dụng với bất kỳ frontend nào (Flask REST API, WebSocket, Tkinter, v.v.).

---

## API của TetrisEngine

```python
from tetris_engine import TetrisEngine

engine = TetrisEngine(seed=42)   # seed tuỳ chọn để tái tạo ván chơi

# Hành động người chơi
engine.action("move_left")
engine.action("move_right")
engine.action("move_down")
engine.action("rotate_cw")
engine.action("rotate_ccw")
engine.action("hard_drop")
engine.action("hold")

# Auto-fall (gọi mỗi fall_speed giây)
engine.tick()

# Lấy toàn bộ trạng thái game
state = engine.get_state()
# state chứa: board, current, next, ghost, held,
#             score, lines, level, combo, game_over, fall_speed
```

---

## Yêu cầu

- Python 3.10+
- pygame