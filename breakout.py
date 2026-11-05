"""
Breakout — a classic brick-breaking game built with pygame.

Controls:
    Mouse or Left/Right arrow keys     — move paddle
    Space or Left click               — launch ball
    R                                — restart (on win/lose screens)
    Esc                              — quit

Five levels: clearing a level's bricks advances to the next layout. Ball
speed rises each level and power-up drops become rarer; level 5 is the
final layout, guarded by indestructible bricks.

Sound effects live in assets/ and are synthesized by make_sounds.py
(rerun it any time to regenerate). All other visuals are pygame.draw
primitives, so the game needs no image assets.

Each entity has a single `draw` method;
to use sprites later, replace the body of those draw methods with
surface.blit(...).
"""

import math
import os
import random
import sys

import pygame

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 800, 600
FPS = 60

# Colors
COLOR_BG = (16, 18, 27)
COLOR_PADDLE = (232, 234, 240)
COLOR_BALL = (255, 255, 255)
COLOR_TEXT = (232, 234, 240)
COLOR_TEXT_DIM = (150, 155, 170)
COLOR_WALL = (60, 64, 80)
COLOR_POWERUP = (255, 210, 64)

# Paddle
PADDLE_WIDTH = 120
PADDLE_HEIGHT = 16
PADDLE_MARGIN_BOTTOM = 40
PADDLE_SPEED = 560  # pixels / second (keyboard)
PADDLE_WIDE_BONUS = 70  # extra width from the WIDE power-up

# Ball
BALL_RADIUS = 8
BALL_SPEED_START = 380
BALL_SPEED_GAIN_PER_BRICK = 6
BALL_SPEED_MAX = 680
PADDLE_MAX_BOUNCE_DEG = 60  # steepest paddle deflection (degrees from vertical)

# Bricks
BRICK_COLS = 8
BRICK_ROWS = 6
BRICK_GAP = 6
# (color, points) per row, top row first
BRICK_ROW_STYLE = [
    ((224, 70, 70), 50),   # red
    ((230, 126, 34), 40),  # orange
    ((241, 196, 23), 30),  # yellow
    ((46, 160, 90), 20),   # green
    ((58, 123, 214), 10),  # blue
    ((147, 88, 204), 10),  # purple
]

# Level data table. Each level is BRICK_ROWS strings of BRICK_COLS chars:
#   '1' one-hit brick    '2' two-hit    '3' three-hit
#   '#' indestructible   '.' empty space
# plus a ball speed multiplier and the power-up drop chance.
LEVELS = [
    {   # Level 1 — baseline
        "name": "BASELINE",
        "speed": 1.00,
        "powerup_chance": 0.18,
        "pattern": [
            "22222222",
            "22222222",
            "11111111",
            "11111111",
            "11111111",
            "11111111",
        ],
    },
    {   # Level 2 — staggered/offset rows, ball +10%
        "name": "STAGGERED",
        "speed": 1.10,
        "powerup_chance": 0.18,
        "pattern": [
            "2222222.",
            ".2222222",
            "1111111.",
            ".1111111",
            "1111111.",
            ".1111111",
        ],
    },
    {   # Level 3 — gaps to work around, ball +20%
        "name": "THE GAPS",
        "speed": 1.20,
        "powerup_chance": 0.15,
        "pattern": [
            "22..22..",
            ".111111.",
            "11....11",
            ".111111.",
            "11....11",
            "..1111..",
        ],
    },
    {   # Level 4 — mostly two-hit bricks, rarer power-ups
        "name": "HARDENED",
        "speed": 1.30,
        "powerup_chance": 0.12,
        "pattern": [
            "22222222",
            "22222222",
            "22222222",
            "22222222",
            "11111111",
            "11111111",
        ],
    },
    {   # Level 5 (final) — indestructible bricks guard the field
        "name": "THE GATE",
        "speed": 1.40,
        "powerup_chance": 0.10,
        "pattern": [
            "22222222",
            "#111111#",
            "#111111#",
            ".111111.",
            ".111111.",
            "22222222",
        ],
    },
]

# Power-ups
POWERUP_SIZE = 18
POWERUP_FALL_SPEED = 130     # pixels / second
POWERUP_DURATION = 10.0      # seconds for timed power-ups

LIVES_START = 3

# Sound effects — generated into assets/ by make_sounds.py
SOUND_NAMES = ("wall", "paddle", "brick", "launch", "powerup",
               "life_lost", "level_up", "game_over", "win")

# Level intro banner
INTRO_DURATION = 2.0  # seconds each level banner is shown

# Game states
STATE_MENU, STATE_SERVE, STATE_PLAY, STATE_WIN, STATE_LOSE = range(5)
STATE_INTRO = 5  # level banner is on screen

# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------


class Paddle:
    def __init__(self):
        self.base_width = PADDLE_WIDTH
        self.height = PADDLE_HEIGHT
        self.y = HEIGHT - PADDLE_MARGIN_BOTTOM - PADDLE_HEIGHT
        self.x = (WIDTH - self.base_width) // 2
        self.wide_until = 0.0  # game-time at which WIDE bonus expires

    @property
    def width(self):
        return self.base_width + (PADDLE_WIDE_BONUS if self.wide_until > 0 else 0)

    def rect(self):
        return pygame.Rect(int(self.x), self.y, int(self.width), self.height)

    def center(self):
        return self.x + self.width / 2, self.y + self.height / 2

    def move(self, dx):
        self.x = max(0, min(WIDTH - self.width, self.x + dx))

    def apply_wide(self, now):
        self.wide_until = max(self.wide_until, now + POWERUP_DURATION)

    def draw(self, surface):
        rect = self.rect()
        wide = self.wide_until > 0
        color = (120, 200, 255) if wide else COLOR_PADDLE
        pygame.draw.rect(surface, color, rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_WALL, rect, width=1, border_radius=8)


class Ball:
    def __init__(self, x, y, speed=BALL_SPEED_START):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.speed = speed
        self.stuck = True  # riding on the paddle until launched

    def launch(self, angle_offset=0.0):
        """Launch upward at a random-ish angle; angle_offset in degrees."""
        angle = math.radians(-90 + angle_offset + random.uniform(-12, 12))
        self.vx = math.cos(angle) * self.speed
        self.vy = math.sin(angle) * self.speed
        self.stuck = False

    def set_speed(self, speed):
        speed = min(BALL_SPEED_MAX, speed)
        if self.stuck or (self.vx == 0 and self.vy == 0):
            self.speed = speed
            return
        factor = speed / max(1e-6, math.hypot(self.vx, self.vy))
        self.vx *= factor
        self.vy *= factor
        self.speed = speed

    def update(self, dt, paddle):
        """Advance the ball; returns a set of collision events
        ("wall" and/or "paddle") for the game to react to."""
        if self.stuck:
            self.x = paddle.center()[0]
            self.y = paddle.y - BALL_RADIUS - 1
            return set()

        events = set()

        # Sub-step so a fast ball can't tunnel through bricks/paddle.
        dist = math.hypot(self.vx, self.vy) * dt
        steps = max(1, int(math.ceil(dist / (BALL_RADIUS * 0.9))))
        step_dt = dt / steps

        for _ in range(steps):
            self.x += self.vx * step_dt
            self.y += self.vy * step_dt

            # Walls
            if self.x - BALL_RADIUS < 0:
                self.x = BALL_RADIUS
                self.vx = abs(self.vx)
                events.add("wall")
            elif self.x + BALL_RADIUS > WIDTH:
                self.x = WIDTH - BALL_RADIUS
                self.vx = -abs(self.vx)
                events.add("wall")
            if self.y - BALL_RADIUS < 0:
                self.y = BALL_RADIUS
                self.vy = abs(self.vy)
                events.add("wall")

            # Paddle: reflect with angle based on hit position
            pr = paddle.rect()
            if (
                self.vy > 0
                and pr.left - BALL_RADIUS <= self.x <= pr.right + BALL_RADIUS
                and pr.top - BALL_RADIUS <= self.y <= pr.bottom + BALL_RADIUS
            ):
                self.y = pr.top - BALL_RADIUS
                offset = (self.x - paddle.center()[0]) / (paddle.width / 2)
                offset = max(-1.0, min(1.0, offset))
                angle = math.radians(-90 + offset * PADDLE_MAX_BOUNCE_DEG)
                self.vx = math.cos(angle) * self.speed
                self.vy = math.sin(angle) * self.speed
                events.add("paddle")

        return events

    def hits_rect(self, rect):
        cx = max(rect.left, min(self.x, rect.right))
        cy = max(rect.top, min(self.y, rect.bottom))
        dx, dy = self.x - cx, self.y - cy
        return dx * dx + dy * dy <= BALL_RADIUS * BALL_RADIUS

    def bounce_off_rect(self, rect):
        """Reflect velocity off the side of a rect the ball penetrated.

        Returns which axis was resolved ('x', 'y', or None).
        """
        # Center of the rect vs the ball tells us the dominant axis.
        dx = self.x - (rect.left + rect.width / 2)
        dy = self.y - (rect.top + rect.height / 2)
        # Normalize by half-extents: |t| > 1 means outside that axis.
        tx = dx / (rect.width / 2 + BALL_RADIUS) if rect.width else 99
        ty = dy / (rect.height / 2 + BALL_RADIUS) if rect.height else 99

        if abs(tx) > abs(ty):
            # Hit a vertical face
            if abs(tx) > 1:
                self.vx = abs(self.vx) if dx > 0 else -abs(self.vx)
                self.x = rect.right + BALL_RADIUS if dx > 0 else rect.left - BALL_RADIUS
                return "x"
        if abs(ty) > 1:
            self.vy = abs(self.vy) if dy > 0 else -abs(self.vy)
            self.y = rect.bottom + BALL_RADIUS if dy > 0 else rect.top - BALL_RADIUS
            return "y"
        # Corner case: nudge off the shallower axis
        if abs(tx) >= abs(ty):
            self.vx = -self.vx
            return "x"
        self.vy = -self.vy
        return "y"

    def draw(self, surface):
        pygame.draw.circle(surface, COLOR_BALL, (int(self.x), int(self.y)), BALL_RADIUS)


class Brick:
    INDESTRUCTIBLE_COLOR = (110, 116, 130)

    def __init__(self, x, y, w, h, color, points, hp=1, indestructible=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = color
        self.points = points
        self.hp = hp
        self.max_hp = hp
        self.alive = True
        self.indestructible = indestructible

    def hit(self):
        """Apply one hit. Returns True only if this hit destroyed the brick.
        Indestructible bricks absorb the hit and return False."""
        if self.indestructible:
            return False
        self.hp -= 1
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def draw(self, surface):
        if not self.alive:
            return
        base = self.color
        if self.indestructible:
            base = self.INDESTRUCTIBLE_COLOR
        elif self.hp < self.max_hp:
            # Cracked / damaged bricks get darker
            base = tuple(int(c * 0.55) for c in base)
        rect = self.rect
        pygame.draw.rect(surface, base, rect, border_radius=4)
        pygame.draw.rect(surface, COLOR_WALL, rect, width=1, border_radius=4)
        # Top highlight for a little depth
        pygame.draw.line(
            surface,
            tuple(min(255, int(c * 1.3)) for c in base),
            (rect.left + 4, rect.top + 2),
            (rect.right - 4, rect.top + 2),
            2,
        )


class PowerUp:
    """A falling bonus pickup.

    The POWERUP_TYPES registry below is the hook for adding new ones:
    add an entry mapping a letter to a `kind` string and implement that
    kind in `Game.on_powerup_caught`.
    """

    TYPES = {
        "W": "wide",    # wider paddle for POWERUP_DURATION seconds
        "M": "multi",   # splits each live ball into three
    }
    LETTERS = list(TYPES.keys())

    def __init__(self, x, y):
        letter = random.choice(self.LETTERS)
        self.letter = letter
        self.kind = self.TYPES[letter]
        self.rect = pygame.Rect(int(x), int(y), POWERUP_SIZE, POWERUP_SIZE)

    def update(self, dt):
        self.rect.y += int(POWERUP_FALL_SPEED * dt)

    def draw(self, surface):
        pygame.draw.rect(
            surface, COLOR_POWERUP, self.rect, border_radius=6
        )
        pygame.draw.rect(surface, COLOR_BG, self.rect, width=1, border_radius=6)
        font = pygame.font.SysFont(None, int(POWERUP_SIZE * 1.2))
        text = font.render(self.letter, True, COLOR_BG)
        surface.blit(
            text,
            text.get_rect(center=(
                self.rect.centerx,
                self.rect.centery
            )),
        )


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont(None, 64)
        self.font_mid = pygame.font.SysFont(None, 34)
        self.font_small = pygame.font.SysFont(None, 24)
        self.sounds = self.load_sounds()
        self.state = STATE_MENU
        self.time = 0.0  # in-game seconds, only advances in serve/play states
        self.reset(full=True)

    # -- setup ------------------------------------------------------------
    def level_def(self):
        return LEVELS[self.level - 1]

    def release_stuck_balls(self):
        """Launch any stuck balls. Returns True if at least one was launched."""
        launched = False
        for ball in self.balls:
            if ball.stuck:
                ball.launch()
                launched = True
        return launched

    # -- sound ------------------------------------------------------------
    @staticmethod
    def load_sounds():
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        sounds = {}
        for name in SOUND_NAMES:
            path = os.path.join(base, name + ".wav")
            if os.path.exists(path):
                try:
                    sounds[name] = pygame.mixer.Sound(path)
                except Exception:
                    pass  # no audio device — the game still runs silently
        return sounds

    def play_sound(self, name):
        sound = self.sounds.get(name)
        if sound is not None:
            try:
                sound.play()
            except Exception:
                pass

    def reset(self, full=True):
        if full:
            self.level = 1
        self.score = 0 if full else self.score
        self.lives = LIVES_START if full else self.lives
        self.start_level()

    def start_level(self):
        # Fresh paddle each level: clears any timed power-up bonuses
        # (e.g. the wide paddle) and recenters it.
        self.paddle = Paddle()
        self.build_bricks()
        self.balls = []
        self.powerups = []
        self.intro_timer = INTRO_DURATION
        self.state = STATE_INTRO

    def build_bricks(self):
        level = self.level_def()
        self.bricks = []
        margin_top = 70
        area_w = WIDTH - 60
        brick_w = (area_w - BRICK_GAP * (BRICK_COLS - 1)) // BRICK_COLS
        brick_h = 26
        x0 = (WIDTH - (brick_w * BRICK_COLS + BRICK_GAP * (BRICK_COLS - 1))) // 2
        for row, pattern_row in enumerate(level["pattern"]):
            color, points = BRICK_ROW_STYLE[row]
            for col, ch in enumerate(pattern_row[:BRICK_COLS]):
                if ch == ".":
                    continue
                x = x0 + col * (brick_w + BRICK_GAP)
                y = margin_top + row * (brick_h + BRICK_GAP)
                if ch == "#":
                    self.bricks.append(Brick(
                        x, y, brick_w, brick_h,
                        Brick.INDESTRUCTIBLE_COLOR, 0,
                        hp=1, indestructible=True,
                    ))
                else:
                    self.bricks.append(Brick(
                        x, y, brick_w, brick_h, color, points, hp=int(ch)
                    ))

    def serve(self):
        base_speed = BALL_SPEED_START * self.level_def()["speed"]
        ball = Ball(self.paddle.center()[0], self.paddle.y, speed=base_speed)
        ball.stuck = True
        self.balls = [ball]
        self.powerups = []
        self.state = STATE_SERVE

    # -- helpers ----------------------------------------------------------
    @staticmethod
    def destructible_bricks(bricks):
        return [b for b in bricks if b.alive and not b.indestructible]

    def render_text(self, text, font, color, center=(WIDTH // 2, HEIGHT // 2)):
        surf = font.render(text, True, color)
        self.screen.blit(surf, surf.get_rect(center=center))

    # -- power-up effects (hook: add new kinds here) ----------------------
    def on_powerup_caught(self, kind):
        if kind == "wide":
            self.paddle.apply_wide(self.time)
        elif kind == "multi":
            new_balls = []
            for ball in self.balls:
                if ball.stuck:
                    continue
                for extra in (-1, 1):
                    clone = Ball(ball.x, ball.y)
                    clone.stuck = False  # clones fly immediately, never ride the paddle
                    base = math.degrees(math.atan2(ball.vy, ball.vx))
                    clone.set_speed(ball.speed)
                    angle = math.radians(base + extra * 20)
                    clone.vx = math.cos(angle) * clone.speed
                    clone.vy = math.sin(angle) * clone.speed
                    if clone.vy > 0:  # keep multi-ball heading upward
                        clone.vy = -abs(clone.vy)
                    new_balls.append(clone)
            self.balls.extend(new_balls)
        # unknown kinds: silently ignore, so partial power-ups never crash

    # -- update -----------------------------------------------------------
    def handle_paddle_input(self, dt, keys):
        dx = 0
        if keys[pygame.K_LEFT]:
            dx -= PADDLE_SPEED
        if keys[pygame.K_RIGHT]:
            dx += PADDLE_SPEED
        if dx:
            self.paddle.move(dx * dt)
        # Mouse follows directly (whichever input is active last wins)
        mouse_x, _ = pygame.mouse.get_pos()
        mouse_visible = pygame.mouse.get_focused()
        if mouse_visible:
            self.paddle.x = max(
                0, min(WIDTH - self.paddle.width, mouse_x - self.paddle.width / 2)
            )

    def update(self, dt):
        if self.state == STATE_INTRO:
            self.intro_timer -= dt
            if self.intro_timer <= 0:
                self.serve()
            return
        if self.state not in (STATE_SERVE, STATE_PLAY):
            return
        self.time += dt

        keys = pygame.key.get_pressed()
        self.handle_paddle_input(dt, keys)

        for ball in self.balls:
            for event in ball.update(dt, self.paddle):
                if event == "paddle":
                    self.play_sound("paddle")
                elif event == "wall":
                    self.play_sound("wall")

        # Ball vs bricks
        for ball in self.balls:
            if ball.stuck:
                continue
            for brick in self.bricks:
                if not brick.alive or not ball.hits_rect(brick.rect):
                    continue
                ball.bounce_off_rect(brick.rect)
                self.play_sound("brick")
                if brick.hit():
                    self.score += brick.points
                    ball.set_speed(ball.speed + BALL_SPEED_GAIN_PER_BRICK)
                    if random.random() < self.level_def()["powerup_chance"]:
                        self.powerups.append(PowerUp(brick.rect.centerx, brick.rect.centery))
                break  # one brick interaction per ball per frame

        # Balls falling off the bottom
        fallen = [b for b in self.balls if b.y - BALL_RADIUS > HEIGHT]
        if fallen:
            self.balls = [b for b in self.balls if b not in fallen]
            if not self.balls:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = STATE_LOSE
                    self.play_sound("game_over")
                else:
                    self.serve()
                    self.play_sound("life_lost")
                return

        # Power-ups falling / caught
        for pu in self.powerups[:]:
            pu.update(dt)
            if pu.rect.bottom > HEIGHT:
                self.powerups.remove(pu)
            elif pu.rect.colliderect(self.paddle.rect()):
                self.play_sound("powerup")
                self.on_powerup_caught(pu.kind)
                self.powerups.remove(pu)

        # Level clear / campaign win
        if not self.destructible_bricks(self.bricks):
            if self.level < len(LEVELS):
                self.level += 1
                self.start_level()
                self.play_sound("level_up")
            else:
                self.score += self.lives * 100  # small life bonus
                self.state = STATE_WIN
                self.play_sound("win")

    # -- draw -------------------------------------------------------------
    def draw(self):
        self.screen.fill(COLOR_BG)

        for brick in self.bricks:
            brick.draw(self.screen)
        for pu in self.powerups:
            pu.draw(self.screen)
        self.paddle.draw(self.screen)
        for ball in self.balls:
            ball.draw(self.screen)

        # HUD
        hud = self.font_mid.render(
            f"Score: {self.score}     Level: {self.level}/{len(LEVELS)}"
            f"     Lives: {self.lives}",
            True, COLOR_TEXT,
        )
        self.screen.blit(hud, (16, 14))

        if self.state == STATE_MENU:
            self.render_text("B R E A K O U T", self.font_big, COLOR_TEXT,
                             (WIDTH // 2, HEIGHT // 2 - 60))
            self.render_text("Mouse or Arrow keys to move  ·  Space to launch",
                             self.font_small, COLOR_TEXT_DIM,
                             (WIDTH // 2, HEIGHT // 2 + 10))
            self.render_text("Press SPACE to start", self.font_mid, COLOR_TEXT,
                             (WIDTH // 2, HEIGHT // 2 + 60))
        elif self.state == STATE_INTRO:
            self.render_text(f"LEVEL {self.level}", self.font_big, COLOR_TEXT,
                             (WIDTH // 2, HEIGHT // 2 - 30))
            self.render_text(self.level_def()["name"], self.font_mid,
                             (120, 200, 255), (WIDTH // 2, HEIGHT // 2 + 30))
        elif self.state == STATE_SERVE:
            self.render_text("Press SPACE to launch", self.font_small,
                             COLOR_TEXT_DIM, (WIDTH // 2, HEIGHT // 2 + 40))
        elif self.state == STATE_WIN:
            self.render_text("YOU WIN!", self.font_big, (90, 220, 140),
                             (WIDTH // 2, HEIGHT // 2 - 40))
            self.render_text(f"All {len(LEVELS)} levels cleared  ·  Score: {self.score}",
                             self.font_mid, COLOR_TEXT, (WIDTH // 2, HEIGHT // 2 + 20))
            self.render_text("Press R to play again  ·  Esc to quit",
                             self.font_small, COLOR_TEXT_DIM,
                             (WIDTH // 2, HEIGHT // 2 + 70))
        elif self.state == STATE_LOSE:
            self.render_text("GAME OVER", self.font_big, (224, 70, 70),
                             (WIDTH // 2, HEIGHT // 2 - 40))
            self.render_text(f"Score: {self.score}", self.font_mid, COLOR_TEXT,
                             (WIDTH // 2, HEIGHT // 2 + 20))
            self.render_text("Press R to try again  ·  Esc to quit",
                             self.font_small, COLOR_TEXT_DIM,
                             (WIDTH // 2, HEIGHT // 2 + 70))

        pygame.display.flip()

    # -- main loop ----------------------------------------------------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False

                if event.key == pygame.K_SPACE:
                    if self.state == STATE_MENU:
                        self.reset(full=True)
                    elif self.state in (STATE_SERVE, STATE_PLAY):
                        if self.release_stuck_balls():
                            self.play_sound("launch")
                        if self.state == STATE_SERVE:
                            self.state = STATE_PLAY

                if event.key == pygame.K_r and self.state in (STATE_WIN, STATE_LOSE):
                    self.reset(full=True)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == STATE_SERVE:
                    self.release_stuck_balls()
                    self.state = STATE_PLAY
                    self.play_sound("launch")
                elif self.state == STATE_PLAY:
                    if self.release_stuck_balls():
                        self.play_sound("launch")

        return True

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 1 / 30)  # clamp huge frame gaps (window drag, lag)
            running = self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()


def main():
    # Match the generated WAVs (44.1 kHz, 16-bit, mono) before init
    pygame.mixer.pre_init(44100, -16, 1, 512)
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Breakout")
    Game(screen).run()


if __name__ == "__main__":
    main()
    sys.exit()
