# BreakEm Power-Up Enhancement Planning

## Project Overview
The goal of this project is to enhance the existing "BreakEm" game by adding
more power-ups, one iteration at a time. The tooling stays the same — plain
Python with `pygame` in `breakem.py`, no new dependencies or assets.

Power-ups come in two flavors:
1. **Time limited** — lasts for a defined duration (in seconds) once obtained.
2. **Session limited** — lasts until the ball is lost and the game resets to its normal state.

## Current State
- The game is implemented in `breakem.py` using `pygame`.
- Power-ups implemented so far:
  - **Wide** — time limited (10 s), wider paddle.
  - **Multi** — instant, splits each live ball into three.
  - **Fast** — time limited (5 s), +50 % ball speed.
  - **Slow** — time limited (5 s), −50 % ball speed.
  - **Double** — time limited (10 s), two paddles side-by-side with a one-paddle-width gap.
- Test harnesses for the power-up behaviors live in `tests/` (headless, SDL dummy drivers).
- The `PowerUp` class handles the falling and catching logic; `Game.on_powerup_caught`
  applies the effects of caught power-ups.
- `Paddle` currently renders a **single** paddle and exposes one collision rect
  (`Paddle.rect()`); the ball reflects off it inside `Ball.update`.

---

## Implemented Enhancement

### 1. Time Limited Speed Power-ups (Fast / Slow)
- **Fast (Boost)**
    - Effect: Increases the speed of all current balls by 50 %.
    - Duration: 5 seconds.
- **Slow**
    - Effect: Decreases the speed of all current balls by 50 %.
    - Duration: 5 seconds.

#### Technical Tasks (completed)

Phase 1 — Analysis & Preparation
- [x] Review `breakem.py` to identify the best locations for new variables and logic.
- [x] Identify how to cleanly handle the `speed_boost` and `speed_reduce` timer to avoid conflicts with brick hits.

Phase 2 — Implementation
- [x] Update `PowerUp.TYPES` to include `FAST` and `SLOW`.
- [x] Modify `Game.on_powerup_caught` to handle the new power-up types.
- [x] Update `Game.serve` to reset session-limited flags.
- [x] Implement the `speed_boost` and `speed_reduce` timers logic in `Game.update`.

Phase 3 — Testing & Refinement
- [x] Verify that "Boost" correctly applies to all balls and expires after 5 seconds.
- [x] Verify that "Slow" correctly applies to all balls and expires after 5 seconds.
- [x] Ensure no regressions in existing power-up behaviors (Wide and Multi).

---

## Implemented Enhancement: Double Paddle

### Overview
A new **"Double"** power-up that **replaces the paddle** for a set duration —
the same 10-second timeout as the existing **Wide** power-up. Instead of a
single paddle, it presents **two paddles side-by-side with a one-paddle-width
gap in the middle**.

- The two side paddles **bounce the ball exactly like a normal paddle**.
- The ball is **free to drop through the central gap**, which causes a **ball loss**.
- It is a risk/reward effect: more surface to save the ball, but a hole in the
  middle to lose it through.

### Specification
| Property   | Value |
| ---------- | ----- |
| Letter     | `D` |
| Kind       | `double` |
| Type       | Paddle replacement, **time limited** |
| Duration   | **10 s** (`POWERUP_DURATION`) — a real game-clock timeout (distinct from Wide, which persists until reset) |
| Layout     | Two paddles, each one base paddle wide, with a **one-paddle-width gap in the middle** (total footprint = 3 × `PADDLE_WIDTH`) |
| Movement   | The two paddles move as a **single unit**, keeping the gap centered |
| Bounce     | Each side paddle reflects the ball normally (angle deflection relative to the *struck* paddle) |
| Gap        | Open — a ball descending through it falls off the bottom and is lost |
| Expiry     | After 10 s the paddle returns to the normal single paddle |

### Design considerations
1. **Multiple collision rects.** `Paddle.rect()` returns one rect and `Ball.update`
   reflects using `paddle.center()`. In Double mode the paddle needs to expose
   **two** rects, and the ball must be tested against each and reflected relative
   to the *struck* paddle's center — not the assembly center.
2. **Ball passing through the gap.** When the ball's x is within the central gap
   while descending, it must **not** reflect; it simply falls. The existing
   fallen-ball check in `Game.update` (ball below `HEIGHT`) already handles the
   resulting ball loss, so no new loss mechanism is required.
3. **Movement stays unit-based.** `paddle.x` / `move(dx)` / mouse-follow can stay,
   reinterpreted as the left edge (or center) of the 3×-wide assembly so the gap
   remains centered.
4. **Interaction with Wide.** Both are paddle-replacement effects. Recommend they be
   **mutually exclusive** (catching one cancels the other), and decide whether a
   Wide bonus width would apply to each Double paddle (recommend: Double uses base width).
5. **Interaction with Multi / Fast / Slow.** Independent (they don't touch the
   paddle), so no direct conflict — but losing a ball is more likely with the gap
   open, so Double is riskier during multi-ball play.
6. **Reset & expiry lifecycle.** The DOUBLE effect expires after 10 s. Because `Paddle` has no
   access to the game clock, `Game.update` reports the current time each frame and the paddle
   ends the effect when it passes the expiry mark (shrinking back to normal while keeping its
   center). It is also cleared on `serve()` / `start_level()` like any fresh paddle.

### Technical Tasks (completed)

#### Phase 1: Analysis & Preparation
- [x] Review `Paddle` and `Ball.update` to plan how to expose multiple paddle rects and per-paddle deflection.
- [x] Decide the Wide/Double interaction (mutual exclusivity and width handling).
- [x] Confirm the existing fallen-ball logic already covers a ball dropping through the gap.

#### Phase 2: Implementation
- [x] Add `"D": "double"` to `PowerUp.TYPES`.
- [x] Extend `Paddle` for Double mode: store `double_until`, add `apply_double(now)`, and expose the active paddle rects plus per-rect centers (e.g. `rects()` / `centers()`).
- [x] Update `Paddle.draw` to render two side-by-side paddles with the central gap when active.
- [x] Update `Ball.update` to reflect off each active paddle rect (relative to that paddle's center) and let the ball pass through the central gap.
- [x] Update `Game.on_powerup_caught` to handle the `"double"` kind (set the timer, cancel a conflicting Wide).
- [x] Update the `serve()` / `start_level()` reset path so the Double effect is cleared like Wide.
- [x] Implement the Wide/Double mutual exclusivity.

#### Phase 3: Testing & Refinement
- [x] Verify the Double layout renders as two paddles with a one-paddle-width central gap.
- [x] Verify both side paddles bounce the ball like a normal paddle.
- [x] Verify a ball dropping through the central gap falls off and causes a ball loss.
- [x] Verify the effect expires after 10 s and the paddle returns to normal.
- [x] Verify serve / new level clears the Double effect.
- [x] Ensure no regressions in existing power-ups (Wide, Multi, Fast, Slow).

Test harness: `tests/test_double_paddle.py` (31 checks, all passing).

---

## Implemented Enhancement: Time-Limited Wide Paddle (10 s)

### Overview
The **Wide** power-up is currently **session limited** — once caught it stays
active until the ball is lost or a new level starts. This enhancement makes it
**time limited**, matching the Double paddle: after catching it, the wide
paddle stays active for **10 seconds**, then automatically reverts to the
basic, stock paddle.

- Duration: **10 s** of game time (the same clock-driven expiry pattern as
  Double, e.g. the existing `POWERUP_DURATION` constant or a dedicated
  `WIDE_DURATION = 10.0` constant).
- On expiry the paddle **shrinks back to `PADDLE_WIDTH` while preserving its
  visual center** (same recentering behavior already used by Double expiry).
- Wide/Double **mutual exclusivity is unchanged** — catching one still cancels
  the other; both are simply paddle replacements with their own timers.

### Specification
| Property   | Value |
| ---------- | ----- |
| Letter     | `W` (unchanged) |
| Kind       | `wide` (unchanged) |
| Type       | Paddle replacement, **time limited** (was: session limited) |
| Duration   | **10 s** on the game clock |
| Expiry     | Paddle reverts to the base single paddle, keeping its current center |
| Reset      | Still cleared by `serve()` / `start_level()` as today (fresh `Paddle`) |

### Design considerations
1. **Reuse the existing expiry mechanism.** `Paddle.refresh(now)` is already
   called every frame from `Game.update` and handles Double expiry. The change
   is to make it also check `wide_until <= now` and revert Wide — no new
   per-frame wiring or new clock plumbing needed.
2. **`apply_wide(now)` sets a real expiry.** Today `wide_until` is set such
   that it never expires (the `wide` check only looks at `wide_until > 0`,
   never against the game clock). It should become `wide_until = now + 10.0`,
   and the `wide` / `width` logic already compares against the stored mark —
   only the value being stored and the expiry path change.
3. **Center preservation on shrink.** When reverting from wide (width =
   `PADDLE_WIDTH + PADDLE_WIDE_BONUS`) to base, adjust `paddle.x` so the
   paddle's center stays put — identical technique to the Double expiry
   recentering. This avoids a visible snap to the left.
4. **Interaction with Double is unchanged.** The two remain mutually
   exclusive; a Wide that expires simply removes the Wide effect and does not
   reactivate Double (Double's own timer already expired or was cancelled
   when Wide was caught).
5. **Interaction with Multi / Fast / Slow.** None — they don't touch the
   paddle. Losing the wide paddle early is not a ball loss, so there is no
   state to reset on expiry beyond the paddle itself.
6. **Behavior change note.** Wide will now wear off mid-life; previously a
   player could hold it forever if they kept the ball in play. This is the
   intended game-balance change.

### Technical Tasks (completed)

#### Phase 1: Analysis & Preparation
- [x] Confirm how `wide_until` is currently set in `apply_wide` and where the
      `wide` check happens (`Paddle.width` / `Paddle.draw`), to scope the edit.
- [x] Confirm `Paddle.refresh(now)` is the single place to add the Wide expiry
      check (mirroring the Double branch).
- [x] Confirm `serve()` / `start_level()` already produce a fresh `Paddle`, so
      the reset path needs no changes.

#### Phase 2: Implementation
- [x] Reuse the existing `POWERUP_DURATION = 10.0` constant (no new constant needed).
- [x] `apply_wide(now)` already stores `wide_until = now + POWERUP_DURATION`; no change needed there.
- [x] Extend `Paddle.refresh(now)` to expire Wide when `wide_until <= now`,
      reverting to base width while preserving the paddle's center.
- [x] Keep the Wide/Double mutual-exclusivity logic unchanged and re-verify it
      still works with the real timer (catching Double still cancels Wide and
      vice versa).

#### Phase 3: Testing & Refinement
- [x] Add checks to `tests/test_powerups.py` (sections 10 / 10b / 10c):
      Wide is still active at t = 9 s, expired at t ≥ 10 s, expiry preserves
      the paddle's visual center, and expiry returns `rects()` to a single
      base-width rect.
- [x] Verify serve / new level still clears Wide.
- [x] Verify Wide/Double mutual exclusivity is unaffected.
- [x] Ensure no regressions in existing power-ups (Multi, Fast, Slow, Double).
- [x] Update `README.md` power-up table: Wide duration becomes "10 seconds".

Test harness: `tests/test_powerups.py` (Wide checks in sections 10 / 10b /
10c; all 70 checks across both harnesses passing).

**Implementation note:** `apply_wide` was already storing a real game-clock
expiry (`wide_until = now + POWERUP_DURATION`) — the only missing piece was
the expiry branch in `Paddle.refresh(now)`, which now reverts Wide to the
base width while preserving the paddle's visual center (same recentering
technique as Double).
