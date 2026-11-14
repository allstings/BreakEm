# Breakout

A classic brick-breaking arcade game built with **Python** and **pygame**.
Clear the bricks, juggle the power-ups, and survive all five increasingly
hard levels — the final one is guarded by indestructible bricks.

All visuals are drawn with `pygame.draw` primitives (no image assets), and
every sound effect is procedurally synthesized — the only assets that ship
are generated `.wav` files.

---

## Features

- **5 hand-designed levels** with rising ball speed and rarer power-up drops.
- **Power-ups** that fall from destroyed bricks (see below).
- **Multi-ball** play, ball speed that ramps up as you clear bricks.
- **3 lives**, per-row brick scoring, and a life bonus for finishing a run.
- **Procedural audio** — 9 sound effects generated from scratch (no downloads).
- **Standalone build** — package as a single-windowed `.exe` with PyInstaller.
- Sub-stepped ball physics so a fast ball can't tunnel through bricks or the paddle.

---

## Requirements

- Python 3.x
- [`pygame`](https://www.pygame.org/) (≥ 2.0)

That's it. No other runtime dependencies.

---

## How to run

### From source

```bash
pip install pygame
python breakout.py
```

### Running the tests

Headless functional tests (no display needed) live in `tests/`:

```bash
python tests/test_double_paddle.py   # Double paddle power-up
python tests/test_powerups.py        # Fast/Slow/Wide/Multi power-ups
```

Both scripts can be run from any directory; they print `[PASS]/[FAIL]` per
check and exit non-zero on any failure.

### Prebuilt executable

A ready-to-run, single-file build is included:

```
dist/Breakout.exe
```

Double-click it (Windows) — no Python installation required. A zip of the
build is also available at `dist/Breakout.zip`.

---

## Controls

| Input                       | Action                          |
| --------------------------- | ------------------------------- |
| Mouse **or** ← / →          | Move the paddle                 |
| **Space** or Left click     | Launch the ball                 |
| **R**                       | Restart (on win/lose screens)   |
| **Esc**                     | Quit                            |

---

## Power-ups

Destroyed bricks have a chance to drop a bonus pickup. Catch it with the
paddle to activate it.

| Letter | Effect | Duration |
| :----: | ------ | -------- |
| **W**  | **Wide** — the paddle gets noticeably wider | until the ball is reset |
| **M**  | **Multi** — each live ball splits into three | instant |
| **F**  | **Fast** — all live balls move **+50 %** faster | 5 seconds |
| **S**  | **Slow** — all live balls move **−50 %** slower | 5 seconds |
| **D**  | **Double** — two paddles side-by-side with an open gap in the middle; the ball bounces off either paddle but can drop through the gap | 10 seconds |

Notes:

- **Wide** and **Double** are both paddle replacements and are mutually
  exclusive — catching one cancels the other.
- **Double** is a risk/reward effect: more paddle surface to save the ball,
  but a one-paddle-width hole in the middle that costs you a ball if you drop
  the ball through it. It times out after 10 seconds and also clears when you
  lose a ball or advance a level.
- **Fast** and **Slow** are mutually exclusive — catching one cancels the
  other. Both expire after 5 seconds and are cleared when you lose a ball or
  advance to a new level.
- The **Fast**/**Slow** effect is a multiplier that composes cleanly with the
  per-brick speed gain, so breaking bricks while boosted doesn't cancel the
  boost (and vice-versa).
- **Multi** clones inherit whatever speed modifier is active when they spawn.

---

## Game flow

1. **Menu** — press **Space** to start.
2. **Level intro** — a short banner shows the level name.
3. **Serve** — the ball rests on the paddle; press **Space** to launch.
4. **Play** — clear every destructible brick to advance to the next level.
   Dropping the last ball costs a life and returns you to the serve state.
5. **Win** — clear all five levels (you get a bonus of `100 × lives remaining`).
6. **Game over** — lose all three lives; press **R** to try again.

Bricks are color-coded by row and worth more points the higher they are.
Bricks marked `#` in a level layout are **indestructible** and must be worked
around.

---

## Project structure

```
Breakout/
├── breakout.py            # the game (single self-contained module)
├── make_sounds.py         # procedural sound-effect generator
├── assets/                # generated .wav sound effects (9 files)
├── planning.md            # power-up enhancement plan & checklist
├── tests/                 # headless power-up test harnesses
│   ├── test_double_paddle.py
│   └── test_powerups.py
├── Breakout.spec          # PyInstaller build configuration
├── dist/                  # build output (Breakout.exe, Breakout.zip)
└── build/                 # PyInstaller intermediate files
```

---

## Regenerating sound effects

All audio is synthesized from sine sweeps, pitched notes, and filtered noise
using only the standard library. To rebuild the `.wav` files from scratch:

```bash
python make_sounds.py
```

This writes fresh 16-bit mono 44.1 kHz WAVs into `assets/` (the same format
the game pre-inits the audio mixer for). The game runs silently if a sound
file or audio device is missing, so it never crashes without sound.

---

## Building the standalone executable

Requirements:

```bash
pip install pyinstaller
```

Build the single-file, windowed (no console) executable:

```bash
pyinstaller Breakout.spec
```

The result is written to `dist/Breakout.exe`. The `assets/` folder is bundled
into the exe automatically (via the spec's `datas`), so the build is fully
self-contained.

> On first run, one-file PyInstaller builds extract to a temporary folder;
> the game reads its assets from that location via `sys._MEIPASS`.

---

## Design notes

- **One file, one idea.** `breakout.py` is intentionally self-contained:
  config constants at the top, then `Paddle`, `Ball`, `Brick`, `PowerUp`,
  and `Game` classes. Each entity has a single `draw` method, so swapping in
  sprites later is a drop-in change.
- **Extensible power-ups.** Add a new pickup by (1) adding a letter → kind
  mapping in `PowerUp.TYPES`, and (2) implementing that kind in
  `Game.on_powerup_caught`. Unknown kinds are ignored safely, so a partial
  power-up can never crash the game.
- **Deterministic timing.** Game time only advances during serve/play, and all
  timed effects are tracked against that clock, so pause-free gameplay stays
  consistent even under frame drops (dt is clamped to 1/30 s).
