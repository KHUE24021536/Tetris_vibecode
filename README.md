# 🎮 Tetris Backend — REST API

Backend cho game Tetris viết bằng **Python + Flask**.  
Thiết kế theo kiến trúc **stateless REST API** — frontend chỉ cần gọi HTTP.

---

## Cấu trúc dự án

```
tetris_backend/
├── tetris_engine.py   # Core game logic (độc lập, không phụ thuộc framework)
├── app.py             # Flask REST API server
├── test_tetris.py     # Unit tests
├── requirements.txt
└── README.md
```

---

## Cài đặt & Chạy

```bash
pip install -r requirements.txt
python app.py
# Server chạy tại http://localhost:22081
```

Chạy tests:
```bash
python test_tetris.py
# hoặc
pytest test_tetris.py -v
```

---

## API Reference

### `GET /api/info`
Xem danh sách tất cả endpoints.

---

### `POST /api/game/new`
Tạo game mới.

**Body (tuỳ chọn):**
```json
{ "player": "Nguyen Van A", "seed": 42 }
```

**Response:**
```json
{
  "game_id": "uuid-here",
  "player": "Nguyen Van A",
  "state": { ... }
}
```

---

### `GET /api/game/<game_id>`
Lấy trạng thái game hiện tại.

**Response `state`:**
```json
{
  "board": [[null, "#00F0F0", ...], ...],  // 20×10 grid
  "current": {
    "type": "T",
    "row": 0, "col": 3, "rotation": 0,
    "cells": [[0,4],[1,3],[1,4],[1,5]],
    "color": "#A000F0"
  },
  "next":  { "type": "I", "color": "...", "cells": [...] },
  "ghost": { ... },   // Bóng mờ — vị trí mảnh sẽ rơi xuống
  "held":  null,      // Mảnh đang giữ (nếu có)
  "score": 0,
  "lines": 0,
  "level": 1,
  "combo": 0,
  "game_over": false,
  "fall_speed": 1.0   // Giây/ô — frontend dùng để set interval
}
```

---

### `POST /api/game/<game_id>/action`
Gửi hành động của người chơi.

**Body:**
```json
{ "action": "move_left" }
```

| Action        | Mô tả                              |
|---------------|------------------------------------|
| `move_left`   | Di chuyển trái                     |
| `move_right`  | Di chuyển phải                     |
| `move_down`   | Soft drop (xuống 1 ô)              |
| `rotate_cw`   | Xoay theo chiều kim đồng hồ        |
| `rotate_ccw`  | Xoay ngược chiều kim đồng hồ       |
| `hard_drop`   | Thả thẳng xuống (cộng điểm bonus)  |
| `hold`        | Giữ mảnh hiện tại                  |

---

### `POST /api/game/<game_id>/tick`
Trigger auto-fall. Frontend gọi theo interval = `state.fall_speed` giây.

---

### `POST /api/game/<game_id>/restart`
Khởi động lại game mới, giữ nguyên `player`.

---

### `GET /api/leaderboard`
Top 10 điểm cao trong session hiện tại.

---

## Ví dụ flow JavaScript (Frontend)

```js
// 1. Tạo game
const { game_id, state } = await fetch('/api/game/new', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ player: 'Player 1' })
}).then(r => r.json());

// 2. Gửi phím bấm
document.addEventListener('keydown', async (e) => {
  const keyMap = {
    ArrowLeft:  'move_left',
    ArrowRight: 'move_right',
    ArrowDown:  'move_down',
    ArrowUp:    'rotate_cw',
    'z':        'rotate_ccw',
    ' ':        'hard_drop',
    'c':        'hold',
  };
  const action = keyMap[e.key];
  if (!action) return;

  const data = await fetch(`/api/game/${game_id}/action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action })
  }).then(r => r.json());

  render(data.state);  // Vẽ lại giao diện
});

// 3. Auto-fall timer
let fallSpeed = state.fall_speed * 1000;  // ms
setInterval(async () => {
  const data = await fetch(`/api/game/${game_id}/tick`, { method: 'POST' })
    .then(r => r.json());
  fallSpeed = data.state.fall_speed * 1000;  // Cập nhật tốc độ theo level
  render(data.state);
}, fallSpeed);
```

---

## Thiết kế kiến trúc

```
┌──────────────┐    HTTP/JSON   ┌────────────────┐
│   Frontend   │ ◄────────────► │  Flask API     │
│  (HTML/JS)   │                │  app.py        │
└──────────────┘                └───────┬────────┘
                                        │ gọi
                                ┌───────▼────────┐
                                │ TetrisEngine   │
                                │ tetris_engine  │
                                │  .py           │
                                └────────────────┘
```

**`TetrisEngine`** hoàn toàn độc lập — có thể dùng lại với bất kỳ framework nào (FastAPI, Django, WebSocket...).

---

## Tính năng đã implement

- ✅ 7 loại Tetromino chuẩn (I, O, T, S, Z, J, L)
- ✅ 7-bag randomizer (phân phối mảnh công bằng)
- ✅ Wall kick khi xoay
- ✅ Ghost piece (bóng mờ)
- ✅ Hold piece
- ✅ Hard drop với điểm bonus
- ✅ Xóa dòng (1, 2, 3, 4 dòng)
- ✅ Combo bonus
- ✅ 10 cấp độ với tốc độ tăng dần
- ✅ Leaderboard
- ✅ CORS support
- ✅ 20 unit tests
