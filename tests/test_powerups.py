"""Headless functional test for the FAST/SLOW power-ups in breakout.py.

Runs without a display (SDL dummy drivers). The core timer/scale logic is
driven deterministically by calling `Game.update_speed_timers()` directly
(avoiding real ball physics / mouse-follow, which don't matter here), plus
one real-frame integration check with the mouse pinned to the paddle.

Asserts the planned behavior:
  * FAST multiplies every live ball's speed by 1.5 for 5 s
  * SLOW  multiplies every live ball's speed by 0.5 for 5 s
  * effects expire after SPEED_MODIFIER_DURATION
  * a brick hit during an effect does NOT cancel it
  * multi-ball clones inherit the active effect
  * serve() (losing the ball) resets the effect to normal
  * existing WIDE + MULTI still work (no regression)

Run:  python tests/test_powerups.py
"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math  # noqa: E402
import pygame  # noqa: E402
import breakout as B  # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f"  ({detail})" if detail else ""))
    if not cond:
        FAILURES.append(name)


def new_game():
    pygame.mixer.pre_init(44100, -16, 1, 512)
    pygame.init()
    screen = pygame.display.set_mode((B.WIDTH, B.HEIGHT))
    pygame.mouse.set_pos((B.WIDTH // 2, B.HEIGHT // 2))  # keep paddle centered
    game = B.Game(screen)
    game.state = B.STATE_PLAY
    return game


def make_ball(game, speed=380.0, angle_deg=-90.0):
    ball = B.Ball(game.paddle.center()[0], game.paddle.y - 20, speed=speed)
    ball.stuck = False
    a = math.radians(angle_deg)
    v = speed * ball.speed_scale
    ball.vx = math.cos(a) * v
    ball.vy = math.sin(a) * v
    return ball


def mag(ball):
    return math.hypot(ball.vx, ball.vy)


def apply_effect(game, kind):
    game.on_powerup_caught(kind)
    game.update_speed_timers()  # push the resolved scale onto the balls


def expire_all(game):
    game.time = max(game.speed_boost_until, game.speed_slow_until) + 0.1
    game.update_speed_timers()


# 1. FAST boosts all balls by 1.5x, base speed untouched -------------------
game = new_game()
balls = [make_ball(game, 380), make_ball(game, 420)]
game.balls = balls
base = [b.speed for b in balls]
apply_effect(game, "fast")
check("FAST sets active scale 1.5", abs(game.active_speed_scale - 1.5) < 1e-9)
check("FAST: ball0 speed = base*1.5", abs(mag(balls[0]) - base[0] * 1.5) < 1e-3)
check("FAST: ball1 speed = base*1.5", abs(mag(balls[1]) - base[1] * 1.5) < 1e-3)
check("FAST leaves base speed unchanged",
      all(b.speed == bb for b, bb in zip(balls, base)))

# 2. Brick hit during FAST keeps the boost (no conflict) -------------------
b = balls[0]
b.set_speed(b.speed + B.BALL_SPEED_GAIN_PER_BRICK)  # simulates a brick hit
check("Brick hit during FAST keeps 1.5x scale",
      abs(mag(b) - b.speed * 1.5) < 1e-3, f"base={b.speed:.1f} mag={mag(b):.1f}")
check("Brick hit still raises base speed",
      b.speed == base[0] + B.BALL_SPEED_GAIN_PER_BRICK)

# 3. FAST expires after 5 s -------------------------------------------------
expire_all(game)
check("FAST expires -> normal scale", abs(game.active_speed_scale - 1.0) < 1e-9)
check("FAST expiry reverts ball speed to base",
      abs(mag(b) - b.speed) < 1e-3)

# 4. SLOW reduces all balls by 0.5x and expires ----------------------------
game = new_game()
balls = [make_ball(game, 400), make_ball(game, 500)]
game.balls = balls
base = [b.speed for b in balls]
apply_effect(game, "slow")
check("SLOW sets active scale 0.5", abs(game.active_speed_scale - 0.5) < 1e-9)
check("SLOW: ball speed = base*0.5",
      all(abs(mag(bb) - bs * 0.5) < 1e-3 for bb, bs in zip(balls, base)))
expire_all(game)
check("SLOW expires -> normal scale", abs(game.active_speed_scale - 1.0) < 1e-9)
check("SLOW expiry reverts ball speed to base",
      all(abs(mag(bb) - bs) < 1e-3 for bb, bs in zip(balls, base)))

# 5. FAST and SLOW are mutually exclusive -----------------------------------
game = new_game()
b = make_ball(game, 400)
game.balls = [b]
apply_effect(game, "fast")
check("FAST active first", abs(game.active_speed_scale - 1.5) < 1e-9)
game.time = 1.0
apply_effect(game, "slow")
check("SLOW overrides active FAST", abs(game.active_speed_scale - 0.5) < 1e-9)
game.time = 1.0
apply_effect(game, "fast")
check("FAST overrides active SLOW", abs(game.active_speed_scale - 1.5) < 1e-9)

# 6. MULTI clones inherit the active effect --------------------------------
game = new_game()
src = make_ball(game, 400)
game.balls = [src]
apply_effect(game, "fast")          # src now at 1.5x
n_before = len(game.balls)
game.on_powerup_caught("multi")
clones = game.balls[n_before:]
check("MULTI still splits into 3", len(game.balls) == 3)
check("MULTI clones inherit 1.5x scale",
      all(abs(c.speed_scale - 1.5) < 1e-9 for c in clones))
check("MULTI clones moving at base*1.5",
      all(abs(mag(c) - c.speed * 1.5) < 1e-3 for c in clones))

# 7. serve() (losing the ball) resets the effect to normal -----------------
game = new_game()
b = make_ball(game, 400)
game.balls = [b]
apply_effect(game, "fast")
check("effect active before serve", abs(game.active_speed_scale - 1.5) < 1e-9)
game.serve()
check("serve resets active scale to 1.0", abs(game.active_speed_scale - 1.0) < 1e-9)
check("serve resets boost timer", game.speed_boost_until == 0.0)
check("new ball has scale 1.0", game.balls[0].speed_scale == 1.0)

# 8. No regression: WIDE still widens paddle; unknown kind ignored ---------
game = new_game()
w0 = game.paddle.width
game.on_powerup_caught("wide")
check("WIDE still works", game.paddle.width == w0 + B.PADDLE_WIDE_BONUS)
game.on_powerup_caught("nonexistent_kind")  # must not raise
check("unknown kind safely ignored", True)

# 10. WIDE is time limited: expires after 10 s ------------------------------
game = new_game()
game.on_powerup_caught("wide")
p = game.paddle
check("WIDE active right after catch", p.wide)
check("WIDE width = base + bonus", p.width == B.PADDLE_WIDTH + B.PADDLE_WIDE_BONUS)
cx = p.center()[0]
p.refresh(game.time + 9.0)
check("WIDE still active at t+9 (<10s)", p.wide)
p.refresh(game.time + 10.0)
check("WIDE expired at t+10 (>=10s)", not p.wide)
check("WIDE expiry: width back to base", p.width == B.PADDLE_WIDTH)
check("WIDE expiry: single base rect",
      len(p.rects()) == 1 and p.rects()[0].width == B.PADDLE_WIDTH)
check("WIDE expiry preserves visual center", abs(p.center()[0] - cx) < 1e-6,
      f"center {cx}->{p.center()[0]}")

# 10b. Integration: real Game.update() frames expire Wide ------------------
game = new_game()
game.balls = []  # no ball, so a ball-loss/serve can't clear it first
game.on_powerup_caught("wide")
check("integration: WIDE active", game.paddle.wide)
for _ in range(int(11 * 60)):
    game.update(1.0 / 60.0)
check("integration: WIDE expired after ~11s of game time",
      not game.paddle.wide)
check("integration: paddle back to base width",
      game.paddle.width == B.PADDLE_WIDTH)

# 10c. serve() still clears Wide (fresh paddle) -----------------------------
game = new_game()
game.on_powerup_caught("wide")
check("serve: WIDE active before serve", game.paddle.wide)
game.serve()
check("serve clears WIDE", not game.paddle.wide)

# 9. Integration: a real Game.update() frame applies the effect ------------
game = new_game()
ball = make_ball(game, 380)
game.balls = [ball]
game.on_powerup_caught("fast")
game.update(1.0 / 60.0)            # one real simulation frame
check("update() applies FAST scale", abs(game.active_speed_scale - 1.5) < 1e-9)
check("update() moves ball at base*1.5", abs(mag(ball) - ball.speed * 1.5) < 1e-3)

print()
if FAILURES:
    print(f"RESULT: {len(FAILURES)} FAILED -> {FAILURES}")
    raise SystemExit(1)
print("RESULT: ALL TESTS PASSED")
pygame.quit()
