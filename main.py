"""
main.py — Giao diện Pygame cho Tetris.
Chạy: python main.py
Yêu cầu: pip install pygame  |  tetris_engine.py phải cùng thư mục
"""

import pygame
import sys
import time
import math
import random
from tetris_engine import TetrisEngine


# ══════════════════════════════════════════════════════════════════════════════
#  CẤU HÌNH
# ══════════════════════════════════════════════════════════════════════════════

BLOCK_SIZE = 30
BOARD_X, BOARD_Y = 165, 40
WIN_W, WIN_H = 640, 700

# Bảng màu — Dark Luxury
COLOR_BG       = (8,   8,  14)
COLOR_GRID     = (22,  22,  35)
COLOR_PANEL_BG = (14,  14,  24)
COLOR_BORDER   = (45,  45,  70)
COLOR_TEXT     = (210, 210, 235)
COLOR_TEXT_DIM = (100, 100, 130)
COLOR_ACCENT   = (80,  200, 255)
COLOR_ACCENT2  = (180,  80, 255)
COLOR_GOLD     = (255, 200,  60)
COLOR_RED      = (255,  60,  80)


# ══════════════════════════════════════════════════════════════════════════════
#  TIỆN ÍCH VẼ
# ══════════════════════════════════════════════════════════════════════════════

def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    for name in ["Consolas", "Courier New", "Lucida Console", "monospace"]:
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            continue
    return pygame.font.SysFont(None, size, bold=bold)


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_block(surface, col, row, hex_color, is_ghost=False, offset=(0, 0)):
    if not hex_color:
        return
    color = pygame.Color(hex_color)
    px = offset[0] + col * BLOCK_SIZE
    py = offset[1] + row * BLOCK_SIZE
    inner = pygame.Rect(px + 2, py + 2, BLOCK_SIZE - 4, BLOCK_SIZE - 4)

    if is_ghost:
        s = pygame.Surface((BLOCK_SIZE - 4, BLOCK_SIZE - 4), pygame.SRCALPHA)
        s.fill((color.r, color.g, color.b, 30))
        surface.blit(s, (px + 2, py + 2))
        pygame.draw.rect(surface, (color.r, color.g, color.b), inner, 1)
    else:
        pygame.draw.rect(surface, (color.r, color.g, color.b), inner, border_radius=2)
        bright = (min(255, color.r + 80), min(255, color.g + 80), min(255, color.b + 80))
        dark   = (max(0,   color.r - 70), max(0,   color.g - 70), max(0,   color.b - 70))
        pygame.draw.line(surface, bright, (px+2, py+2), (px+BLOCK_SIZE-3, py+2))
        pygame.draw.line(surface, bright, (px+2, py+2), (px+2, py+BLOCK_SIZE-3))
        pygame.draw.line(surface, dark,   (px+2, py+BLOCK_SIZE-3), (px+BLOCK_SIZE-3, py+BLOCK_SIZE-3))
        pygame.draw.line(surface, dark,   (px+BLOCK_SIZE-3, py+2), (px+BLOCK_SIZE-3, py+BLOCK_SIZE-3))
        # Shine dot
        shine = (min(255, color.r+120), min(255, color.g+120), min(255, color.b+120))
        pygame.draw.rect(surface, shine, pygame.Rect(px+4, py+4, BLOCK_SIZE//4, BLOCK_SIZE//4), border_radius=1)


def draw_glowing_rect(surface, rect, color, radius=6, glow_strength=3):
    """Panel với viền phát sáng nhiều lớp."""
    for i in range(glow_strength, 0, -1):
        alpha = int(55 / i)
        s = pygame.Surface((rect.width + i*4, rect.height + i*4), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha),
                         pygame.Rect(0, 0, rect.width + i*4, rect.height + i*4),
                         border_radius=radius + i)
        surface.blit(s, (rect.x - i*2, rect.y - i*2))
    pygame.draw.rect(surface, COLOR_PANEL_BG, rect, border_radius=radius)
    pygame.draw.rect(surface, color, rect, 1, border_radius=radius)


def draw_piece_preview(surface, cells, color, panel_rect, y_offset=22):
    if not cells:
        return
    rows = [r for r, c in cells]
    cols = [c for r, c in cells]
    min_r, max_r = min(rows), max(rows)
    min_c, max_c = min(cols), max(cols)
    piece_w = (max_c - min_c + 1) * BLOCK_SIZE
    piece_h = (max_r - min_r + 1) * BLOCK_SIZE
    ox = panel_rect.x + (panel_rect.width  - piece_w) // 2
    oy = panel_rect.y + y_offset + (panel_rect.height - y_offset - piece_h) // 2
    for r, c in cells:
        draw_block(surface, c - min_c, r - min_r, color, offset=(ox, oy))


# ══════════════════════════════════════════════════════════════════════════════
#  PARTICLES
# ══════════════════════════════════════════════════════════════════════════════

class Particle:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        angle = random.uniform(0, math.tau)
        speed = random.uniform(1, 4)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - random.uniform(1, 3)
        self.life = 1.0
        self.decay = random.uniform(0.02, 0.05)
        self.size = random.randint(2, 5)
        self.color = color

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.12
        self.life -= self.decay

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = int(255 * self.life)
        s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
        c = pygame.Color(self.color)
        pygame.draw.circle(s, (c.r, c.g, c.b, alpha), (self.size, self.size), self.size)
        surface.blit(s, (int(self.x) - self.size, int(self.y) - self.size))


# ══════════════════════════════════════════════════════════════════════════════
#  STARS BACKGROUND
# ══════════════════════════════════════════════════════════════════════════════

class Star:
    def __init__(self):
        self.reset(initial=True)

    def reset(self, initial=False):
        self.x = random.randint(0, WIN_W)
        self.y = random.randint(0, WIN_H) if initial else 0
        self.size = random.uniform(0.5, 2.0)
        self.brightness = random.uniform(0.3, 1.0)
        self.speed = random.uniform(0.1, 0.4)

    def update(self):
        self.y += self.speed
        if self.y > WIN_H:
            self.reset()

    def draw(self, surface):
        b = int(self.brightness * 180)
        pygame.draw.circle(surface, (b, b, b + 40), (int(self.x), int(self.y)), int(self.size))


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("TETRIS  ✦  NoBug Stars Edition")
    pygame.key.set_repeat(180, 55)
    clock = pygame.time.Clock()

    # Fonts
    font_label = get_font(11, bold=True)
    font_val   = get_font(20, bold=True)
    font_mid   = get_font(20)
    font_big   = get_font(52, bold=True)

    # Nền sao
    stars = [Star() for _ in range(80)]

    # State
    engine: TetrisEngine | None = None
    last_tick    = time.time()
    game_started = False
    running      = True
    t            = 0.0
    prev_lines   = 0
    particles: list[Particle] = []

    while running:
        dt = clock.tick(60) / 1000.0
        t += dt
        state = engine.get_state() if engine else None

        # ── Events ──────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if not game_started:
                    if event.key == pygame.K_RETURN:
                        engine = TetrisEngine()
                        last_tick = time.time()
                        game_started = True
                        prev_lines = 0

                elif state and state["game_over"]:
                    if event.key == pygame.K_RETURN:
                        engine = TetrisEngine()
                        last_tick = time.time()
                        prev_lines = 0
                        particles.clear()

                elif state:
                    actions = {
                        pygame.K_LEFT:  "move_left",
                        pygame.K_RIGHT: "move_right",
                        pygame.K_DOWN:  "move_down",
                        pygame.K_UP:    "rotate_cw",
                        pygame.K_z:     "rotate_ccw",
                        pygame.K_SPACE: "hard_drop",
                        pygame.K_c:     "hold",
                    }
                    if event.key in actions:
                        engine.action(actions[event.key])

        # ── Logic ────────────────────────────────────────────────────────────
        if game_started and state and not state["game_over"]:
            if time.time() - last_tick >= state["fall_speed"]:
                engine.tick()
                last_tick = time.time()

            # Phát hiện line clear → spawn particles
            cur_lines = state["lines"]
            if cur_lines > prev_lines:
                colors = ["#00F0F0", "#F0F000", "#A000F0", "#00F000", "#F0A000"]
                for _ in range((cur_lines - prev_lines) * 28):
                    px = BOARD_X + random.randint(0, 300)
                    py = BOARD_Y + random.randint(0, 600)
                    particles.append(Particle(px, py, random.choice(colors)))
            prev_lines = cur_lines

        # Update
        particles = [p for p in particles if p.life > 0]
        for p in particles:
            p.update()
        for s in stars:
            s.update()

        # ── Render ───────────────────────────────────────────────────────────
        screen.fill(COLOR_BG)
        for s in stars:
            s.draw(screen)

        # ── Start Screen ─────────────────────────────────────────────────────
        if not game_started:
            pulse = 0.5 + 0.5 * math.sin(t * 2.5)
            title_color = lerp_color(COLOR_ACCENT, COLOR_ACCENT2, pulse)
            title_surf = font_big.render("TETRIS", True, title_color)

            glow_s = pygame.Surface((title_surf.get_width() + 60, title_surf.get_height() + 40), pygame.SRCALPHA)
            pygame.draw.ellipse(glow_s, (*title_color, 25),
                                pygame.Rect(0, 0, glow_s.get_width(), glow_s.get_height()))
            screen.blit(glow_s, (WIN_W//2 - glow_s.get_width()//2, WIN_H//2 - 90))
            screen.blit(title_surf, (WIN_W//2 - title_surf.get_width()//2, WIN_H//2 - 80))

            tag = font_label.render("NoBug Stars Edition", True, COLOR_TEXT_DIM)
            screen.blit(tag, (WIN_W//2 - tag.get_width()//2, WIN_H//2 - 10))

            if int(t * 2) % 2 == 0:
                prompt = font_mid.render("[ ENTER ]  to play", True, COLOR_ACCENT)
                screen.blit(prompt, (WIN_W//2 - prompt.get_width()//2, WIN_H//2 + 40))

            hints = [
                ("←  →",  "Di chuyển"),
                ("↑  Z",  "Xoay"),
                ("↓",     "Rơi chậm"),
                ("Space", "Hard Drop"),
                ("C",     "Hold"),
            ]
            hx, hy = WIN_W//2 - 110, WIN_H//2 + 110
            for i, (key, desc) in enumerate(hints):
                screen.blit(font_label.render(key,  True, COLOR_GOLD),     (hx,      hy + i*22))
                screen.blit(font_label.render(desc, True, COLOR_TEXT_DIM), (hx + 80, hy + i*22))

        # ── Game Screen ──────────────────────────────────────────────────────
        elif state is not None:
            # Board
            board_rect = pygame.Rect(BOARD_X, BOARD_Y, 300, 600)
            pygame.draw.rect(screen, (4, 4, 10), board_rect)

            for x in range(11):
                pygame.draw.line(screen, COLOR_GRID,
                                 (BOARD_X + x*BLOCK_SIZE, BOARD_Y),
                                 (BOARD_X + x*BLOCK_SIZE, BOARD_Y + 600))
            for y in range(21):
                pygame.draw.line(screen, COLOR_GRID,
                                 (BOARD_X, BOARD_Y + y*BLOCK_SIZE),
                                 (BOARD_X + 300, BOARD_Y + y*BLOCK_SIZE))

            for r in range(20):
                for c in range(10):
                    if state["board"][r][c]:
                        draw_block(screen, c, r, state["board"][r][c], offset=(BOARD_X, BOARD_Y))

            if not state["game_over"]:
                if state["ghost"]:
                    for r, c in state["ghost"]["cells"]:
                        draw_block(screen, c, r, state["current"]["color"],
                                   is_ghost=True, offset=(BOARD_X, BOARD_Y))
                for r, c in state["current"]["cells"]:
                    draw_block(screen, c, r, state["current"]["color"], offset=(BOARD_X, BOARD_Y))

            # Viền board nhịp thở
            pulse = 0.5 + 0.5 * math.sin(t * 1.5)
            border_col = lerp_color(COLOR_BORDER, COLOR_ACCENT, pulse * 0.4)
            pygame.draw.rect(screen, border_col, board_rect.inflate(2, 2), 2, border_radius=2)

            # ── Panel trái ───────────────────────────────────────────────────
            hold_rect = pygame.Rect(18, BOARD_Y, 132, 110)
            draw_glowing_rect(screen, hold_rect, COLOR_ACCENT2, radius=8, glow_strength=2)
            lbl = font_label.render("H O L D", True, COLOR_ACCENT2)
            screen.blit(lbl, (hold_rect.x + (hold_rect.width - lbl.get_width())//2, hold_rect.y + 8))
            if state["held"]:
                draw_piece_preview(screen, state["held"]["cells"], state["held"]["color"], hold_rect)

            ctrl_y = BOARD_Y + 128
            for k, d in [("←→","Move"), ("↑Z","Rotate"), ("↓","Soft"), ("SPC","Drop"), ("C","Hold")]:
                screen.blit(font_label.render(k, True, COLOR_GOLD),     (20, ctrl_y))
                screen.blit(font_label.render(d, True, COLOR_TEXT_DIM), (58, ctrl_y))
                ctrl_y += 20

            # ── Panel phải ───────────────────────────────────────────────────
            rx = BOARD_X + 310

            next_rect = pygame.Rect(rx, BOARD_Y, 130, 110)
            draw_glowing_rect(screen, next_rect, COLOR_ACCENT, radius=8, glow_strength=2)
            lbl = font_label.render("N E X T", True, COLOR_ACCENT)
            screen.blit(lbl, (next_rect.x + (next_rect.width - lbl.get_width())//2, next_rect.y + 8))
            if state["next"]:
                draw_piece_preview(screen, state["next"]["cells"], state["next"]["color"], next_rect)

            stats_rect = pygame.Rect(rx, BOARD_Y + 125, 130, 290)
            draw_glowing_rect(screen, stats_rect, COLOR_BORDER, radius=8, glow_strength=1)

            combo_col = COLOR_RED if state["combo"] >= 2 else COLOR_TEXT_DIM
            stats_data = [
                ("SCORE", str(state["score"]),  COLOR_GOLD),
                ("LEVEL", str(state["level"]),  COLOR_ACCENT),
                ("LINES", str(state["lines"]),  COLOR_ACCENT2),
                ("COMBO", f"×{state['combo']}", combo_col),
            ]
            sy = stats_rect.y + 16
            for label, val, col in stats_data:
                screen.blit(font_label.render(label, True, COLOR_TEXT_DIM), (stats_rect.x + 12, sy))
                sy += 16
                screen.blit(font_val.render(val, True, col), (stats_rect.x + 12, sy))
                sy += 30
                pygame.draw.line(screen, COLOR_BORDER,
                                 (stats_rect.x + 8, sy), (stats_rect.right - 8, sy))
                sy += 8

            # Level progress bar
            bar_rect = pygame.Rect(rx, BOARD_Y + 430, 130, 16)
            draw_glowing_rect(screen, bar_rect, COLOR_BORDER, radius=4, glow_strength=1)
            fill_w = int((state["lines"] % 10) / 10 * (bar_rect.width - 4))
            if fill_w > 0:
                pygame.draw.rect(screen, COLOR_ACCENT,
                                 pygame.Rect(bar_rect.x + 2, bar_rect.y + 2, fill_w, bar_rect.height - 4),
                                 border_radius=3)
            prog_lbl = font_label.render("NEXT LV", True, COLOR_TEXT_DIM)
            screen.blit(prog_lbl, (rx + (130 - prog_lbl.get_width())//2, BOARD_Y + 452))

            spd = font_label.render(f"SPD  {state['fall_speed']:.3f}s", True, COLOR_TEXT_DIM)
            screen.blit(spd, (rx + 10, BOARD_Y + 472))

            # Particles
            for p in particles:
                p.draw(screen)

            # ── Game Over overlay ─────────────────────────────────────────────
            if state["game_over"]:
                overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 215))
                screen.blit(overlay, (0, 0))

                pulse2 = 0.5 + 0.5 * math.sin(t * 4)
                red_col = lerp_color(COLOR_RED, (255, 160, 60), pulse2)
                over_surf = font_big.render("GAME OVER", True, red_col)
                screen.blit(over_surf, (WIN_W//2 - over_surf.get_width()//2, WIN_H//2 - 80))

                score_s = font_val.render(f"Score: {state['score']}", True, COLOR_GOLD)
                screen.blit(score_s, (WIN_W//2 - score_s.get_width()//2, WIN_H//2 - 10))

                info_s = font_mid.render(f"Lines: {state['lines']}   Level: {state['level']}",
                                         True, COLOR_TEXT_DIM)
                screen.blit(info_s, (WIN_W//2 - info_s.get_width()//2, WIN_H//2 + 25))

                if int(t * 2) % 2 == 0:
                    restart = font_mid.render("[ ENTER ]  to restart", True, COLOR_ACCENT)
                    screen.blit(restart, (WIN_W//2 - restart.get_width()//2, WIN_H//2 + 75))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()