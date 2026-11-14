# Breakout Power-Up Enhancement Planning

## Project Overview
The goal of this project is to enhance the existing "Breakout" game by adding
more power-ups, one iteration at a time. The tooling stays the same — plain
Python with `pygame` in `breakout.py`, no new dependencies or assets.

Power-ups come in two flavors:
1. **Time limited** — lasts for a defined duration (in seconds) once obtained.
2. **Session limited** — lasts until the ball is lost and the game resets to its normal state.

## Current State
- The game is implemented in `breakout.py` using `pygame`.
- Power-ups implemented so far:
  - **Wide** — session limited (persists until the ball is lost / a new level), wider paddle.
  - **Multi** — instant, splits each live ball into three.
  - **Fast** — time limited (5 s), +50 % ball speed.
  - **Slow** — time limited (5 s), −50 % ball speed.
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
- [x] Review `breakout.py` to identify the best locations for new variables and logic.
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

## Proposed Enhancement: Double Paddle

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

### Technical Tasks

#### Phase 1: Analysis & Preparation
- [ ] Review `Paddle` and `Ball.update` to plan how to expose multiple paddle rects and per-paddle deflection.
- [ ] Decide the Wide/Double interaction (mutual exclusivity and width handling).
- [ ] Confirm the existing fallen-ball logic already covers a ball dropping through the gap.

#### Phase 2: Implementation
- [ ] Add `"D": "double"` to `PowerUp.TYPES`.
- [ ] Extend `Paddle` for Double mode: store `double_until`, add `apply_double(now)`, and expose the active paddle rects plus per-rect centers (e.g. `rects()` / `centers()`).
- [ ] Update `Paddle.draw` to render two side-by-side paddles with the central gap when active.
- [ ] Update `Ball.update` to reflect off each active paddle rect (relative to that paddle's center) and let the ball pass through the central gap.
- [ ] Update `Game.on_powerup_caught` to handle the `"double"` kind (set the timer, cancel a conflicting Wide).
- [ ] Update the `serve()` / `start_level()` reset path so the Double effect is cleared like Wide.
- [ ] Implement the Wide/Double mutual exclusivity.

#### Phase 3: Testing & Refinement
- [ ] Verify the Double layout renders as two paddles with a one-paddle-width central gap.
- [ ] Verify both side paddles bounce the ball like a normal paddle.
- [ ] Verify a ball dropping through the central gap falls off and causes a ball loss.
- [ ] Verify the effect expires after 10 s and the paddle returns to normal.
- [ ] Verify serve / new level clears the Double effect.
- [ ] Ensure no regressions in existing power-ups (Wide, Multi, Fast, Slow).
