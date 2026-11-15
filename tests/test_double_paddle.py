"""Headless functional test for the DOUBLE paddle power-up in breakem.py.

Runs without a display (SDL dummy drivers). Verifies:
  * layout = two base-width paddles with a one-paddle-width central gap
  * both side paddles bounce the ball normally (deflection relative to the
    struck paddle)
  * the ball falls straight through the central gap (no bounce)
  * the effect expires after 10 s (POWERUP_DURATION), keeping its center
  * Wide / Double are mutually exclusive
  * serve() clears the Double effect
  * no regression to the single (normal / wide) paddle

Run:  python tests/test_double_paddle.py
"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402
import breakem as B  # noqa: E402

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


def down_ball(paddle, x):
    """A ball just above the paddle, moving straight down."""
    b = B.Ball(x, paddle.y - 4, speed=380.0)
    b.stuck = False
    b.vx = 0.0
    b.vy = 380.0
    return b


# 1. Layout / geometry ------------------------------------------------------
p = B.Paddle()
check("normal: single rect", len(p.rects()) == 1)
check("normal: width = base", p.width == B.PADDLE_WIDTH)
p.apply_double(0.0)
rs = p.rects()
check("double: active", p.double)
check("double: two rects", len(rs) == 2)
check("double: each paddle base-wide",
      rs[0].width == B.PADDLE_WIDTH and rs[1].width == B.PADDLE_WIDTH)
gap = rs[1].left - rs[0].right
check("double: gap = one paddle width", gap == B.PADDLE_WIDTH, f"gap={gap}")
check("double: footprint = 3x base", p.width == B.PADDLE_WIDTH * 3,
      f"width={p.width}")
cx = p.x + p.width / 2
check("double: gap centered in footprint",
      abs((rs[0].right + rs[1].left) / 2 - cx) < 1e-6)
paddle_top = p.y
gapc = (rs[0].right + rs[1].left) / 2

# 2. Both side paddles bounce the ball --------------------------------------
b = down_ball(p, rs[0].centerx)
b.update(1.0 / 60.0, p)
check("left paddle bounces (vy up)", b.vy < 0, f"vy={b.vy:.1f}")
b = down_ball(p, rs[1].centerx)
b.update(1.0 / 60.0, p)
check("right paddle bounces (vy up)", b.vy < 0, f"vy={b.vy:.1f}")

# 3. Ball falls through the central gap -------------------------------------
b = down_ball(p, gapc)
y0 = b.y
b.update(1.0 / 60.0, p)
check("gap: no bounce (vy still down)", b.vy > 0, f"vy={b.vy:.1f}")
check("gap: ball passes below its start", b.y > y0, f"y {y0:.1f}->{b.y:.1f}")

# 4. Deflection is relative to the struck paddle ----------------------------
b = B.Ball(rs[0].left + 1, paddle_top - 4, speed=380.0)
b.stuck = False
b.vx = 0.0
b.vy = 380.0
b.update(1.0 / 60.0, p)
check("left-edge hit deflects left (vx<0)", b.vx < 0, f"vx={b.vx:.1f}")
b = B.Ball(rs[1].right - 1, paddle_top - 4, speed=380.0)
b.stuck = False
b.vx = 0.0
b.vy = 380.0
b.update(1.0 / 60.0, p)
check("right-edge hit deflects right (vx>0)", b.vx > 0, f"vx={b.vx:.1f}")

# 5. 10-second timeout ------------------------------------------------------
p = B.Paddle()
p.apply_double(0.0)
cx = p.x + p.width / 2
p.refresh(9.0)
check("double still active at t=9 (<10s)", p.double)
p.refresh(11.0)
check("double expired at t=11 (>=10s)", not p.double)
check("expired: reverts to single rect", len(p.rects()) == 1)
check("expired: width back to base", p.width == B.PADDLE_WIDTH)
check("expiry preserves visual center", abs(p.x + p.width / 2 - cx) < 1e-6,
      f"center {cx}->{p.x + p.width / 2}")

# 6. Wide / Double mutual exclusivity ---------------------------------------
p = B.Paddle()
p.apply_wide(0.0)
check("wide active initially", p.wide)
p.apply_double(0.0)
check("double active after catching double", p.double)
check("wide cleared after catching double", not p.wide,
      f"wide_until={p.wide_until}")
p = B.Paddle()
p.apply_double(0.0)
p.apply_wide(0.0)
check("wide active after catching wide", p.wide)
check("double cleared after catching wide", not p.double,
      f"double_active={p.double_active}")

# 7. serve() clears the Double effect ---------------------------------------
game = new_game()
game.paddle.apply_double(game.time)
check("double active before serve", game.paddle.double)
game.serve()
check("serve clears double", not game.paddle.double)
check("serve paddle is single rect", len(game.paddle.rects()) == 1)

# 8. No regression: normal / wide stay a single rect ------------------------
p = B.Paddle()
check("regression: normal single rect", len(p.rects()) == 1)
p.apply_wide(0.0)
check("regression: wide single wide rect",
      len(p.rects()) == 1
      and p.rects()[0].width == B.PADDLE_WIDTH + B.PADDLE_WIDE_BONUS)

# 9. Integration: real Game.update() frames expire the Double effect --------
game = new_game()
game.balls = []  # no ball, so a ball-loss/serve can't clear it first
game.paddle.apply_double(game.time)
check("integration: double active", game.paddle.double)
for _ in range(int(11 * 60)):
    game.update(1.0 / 60.0)
check("integration: double expired after ~11s of game time",
      not game.paddle.double)

# 10. Power-up catch surfaces while Double is active (THE BUG FIX) ---------
#     Catch must test BOTH side paddles; the central gap must fall through.
p = B.Paddle()
p.apply_double(0.0)
rs = p.rects()
left, right = rs[0], rs[1]
gap_cx = (left.right + right.left) // 2

def pu_at(cx):
    """A power-up rect centered on x=`cx` at paddle height."""
    r = pygame.Rect(0, 0, B.POWERUP_SIZE, B.POWERUP_SIZE)
    r.center = (int(cx), p.y + p.height // 2)
    return r

check("catch: power-up over LEFT paddle is caught", p.catches(pu_at(left.centerx)))
check("catch: power-up over RIGHT paddle is caught", p.catches(pu_at(right.centerx)))
check("catch: power-up over the central GAP is NOT caught", not p.catches(pu_at(gap_cx)))
check("catch: normal paddle still catches on its single surface",
      B.Paddle().catches(pu_at(B.WIDTH // 2)))

# 10b. Integration: a dropped power-up on the RIGHT paddle is caught by real
#     Game.update() and applies its effect (was silently missed before the fix)
game = new_game()
game.balls = []  # no ball, so a ball-loss/serve can't interfere
game.paddle.apply_double(game.time)
C = B.WIDTH // 2
# Park the paddle so its center is at C, and pin the mouse there so the
# mouse-follow keeps it put through the update frame.
game.paddle.x = C - game.paddle.width / 2
pygame.mouse.set_pos((C, B.HEIGHT // 2))
right = game.paddle.rects()[1]
pu = B.PowerUp(right.centerx, right.centery)
pu.letter, pu.kind = "F", "fast"
pu.rect.center = (right.centerx, right.centery)
game.powerups = [pu]
boost_before = game.speed_boost_until
game.update(1.0 / 60.0)
check("integration: right-paddle power-up is removed (caught)",
      pu not in game.powerups)
check("integration: caught power-up applied its effect (fast timer set)",
      game.speed_boost_until > boost_before)

# 10c. Integration: a power-up over the GAP is NOT caught (falls through) ----
game = new_game()
game.balls = []
game.paddle.apply_double(game.time)
C = B.WIDTH // 2
game.paddle.x = C - game.paddle.width / 2
pygame.mouse.set_pos((C, B.HEIGHT // 2))
rs = game.paddle.rects()
gap_cx = (rs[0].right + rs[1].left) // 2
pu = B.PowerUp(gap_cx, rs[0].centery)
pu.letter, pu.kind = "F", "fast"
pu.rect.center = (gap_cx, rs[0].centery)
game.powerups = [pu]
game.update(1.0 / 60.0)
check("integration: gap power-up is NOT caught (still falling)",
      pu in game.powerups)
check("integration: gap power-up applied no effect",
      game.speed_boost_until == 0.0)

print()
if FAILURES:
    print(f"RESULT: {len(FAILURES)} FAILED -> {FAILURES}")
    raise SystemExit(1)
print("RESULT: ALL TESTS PASSED")
pygame.quit()
