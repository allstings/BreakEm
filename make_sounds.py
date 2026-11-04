"""
Procedural sound-effect generator for Breakout.

No external assets or libraries needed — every effect is synthesized
from sine sweeps, notes and filtered noise using only the Python
standard library, then written as 16-bit mono 44.1 kHz WAV files
into ./assets/ where breakout.py loads them at startup.

Run:  python make_sounds.py
"""

import math
import os
import random
import struct
import wave

SAMPLE_RATE = 44100
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# ---------------------------------------------------------------------------
# primitives
# ---------------------------------------------------------------------------


def n_samples(duration):
    return int(SAMPLE_RATE * duration)


def envelope_exp(i, n, k=18.0):
    """Exponential decay envelope."""
    return math.exp(-k * i / max(1, n))


def envelope_note(i, n, attack=0.02, release=0.25):
    """Short attack, exponential-ish release, for pitched notes."""
    a = max(1, int(n * attack))
    if i < a:
        return i / a
    t = (i - a) / max(1, n - a)
    return (1 - t) ** release


def sine(freq, duration, vol=0.8):
    n = n_samples(duration)
    phase = 0.0
    out = []
    for i in range(n):
        phase += 2 * math.pi * freq / SAMPLE_RATE
        out.append(vol * envelope_exp(i, n) * math.sin(phase))
    return out


def sweep(f0, f1, duration, vol=0.8, k=14.0):
    """Linear frequency sweep from f0 to f1."""
    n = n_samples(duration)
    phase = 0.0
    out = []
    for i in range(n):
        t = i / max(1, n - 1)
        freq = f0 + (f1 - f0) * t
        phase += 2 * math.pi * freq / SAMPLE_RATE
        out.append(vol * envelope_exp(i, n, k) * math.sin(phase))
    return out


def noise_burst(duration, vol=0.5, lowpass=0.35, k=30.0):
    """White noise through a one-pole lowpass, exponentially decayed."""
    n = n_samples(duration)
    out = []
    prev = 0.0
    for i in range(n):
        target = random.uniform(-1.0, 1.0)
        prev = prev + lowpass * (target - prev)
        out.append(vol * envelope_exp(i, n, k) * prev)
    return out


def mix(*parts):
    """Sum sample lists (padded to the longest), clipping to [-1, 1]."""
    length = max(len(p) for p in parts)
    out = [0.0] * length
    for part in parts:
        for i, s in enumerate(part):
            out[i] += s
    return [max(-1.0, min(1.0, s)) for s in out]


def note(freq, duration, vol=0.7, k=6.0):
    """A pitched note with attack + release envelope."""
    n = n_samples(duration)
    phase = 0.0
    out = []
    for i in range(n):
        phase += 2 * math.pi * freq / SAMPLE_RATE
        out.append(vol * envelope_note(i, n) * math.sin(phase))
    return out


def sequence(parts):
    """Concatenate sample lists end to end."""
    out = []
    for part in parts:
        out.extend(part)
    return out


def chord(parts, duration=None, vol_scale=1.0):
    """Play parts simultaneously for the longest one's length."""
    if duration is None:
        duration = max(len(p) for p in parts) / SAMPLE_RATE
    length = n_samples(duration)
    out = [0.0] * length
    for part in parts:
        for i in range(min(length, len(part))):
            out[i] += vol_scale * part[i]
    return [max(-1.0, min(1.0, s)) for s in out]


def write_wav(name, samples):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name + ".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        frames = b"".join(
            struct.pack("<h", int(s * 32767)) for s in samples
        )
        w.writeframes(frames)
    return path, len(samples) / SAMPLE_RATE


# ---------------------------------------------------------------------------
# sound design
# ---------------------------------------------------------------------------

SOUNDS = {
    # Short, dry "tick" for wall bounces.
    "wall": lambda: mix(sine(260, 0.03, 0.45), noise_burst(0.02, 0.15)),

    # Low "tock" for the paddle.
    "paddle": lambda: mix(sine(150, 0.07, 0.8), noise_burst(0.03, 0.25, 0.5)),

    # Bright descending "pop" for breaking a brick.
    "brick": lambda: mix(sweep(560, 260, 0.09, 0.8), noise_burst(0.05, 0.3)),

    # Quick rising blip when the ball is launched.
    "launch": lambda: sweep(220, 680, 0.10, 0.7, k=8.0),

    # Three-note ascending arpeggio for catching a power-up.
    "powerup": lambda: sequence([
        note(523.25, 0.08, 0.6),
        note(783.99, 0.08, 0.6),
        note(1046.5, 0.14, 0.7),
    ]),

    # Long descending groan for losing a life.
    "life_lost": lambda: mix(sweep(340, 70, 0.40, 0.8, k=5.0),
                             sine(60, 0.30, 0.5)),

    # Four-note rising fanfare for clearing a level.
    "level_up": lambda: sequence([
        note(440.0, 0.09, 0.6),
        note(554.37, 0.09, 0.6),
        note(659.25, 0.09, 0.6),
        note(880.0, 0.22, 0.7),
    ]),

    # Three slow descending notes for game over.
    "game_over": lambda: sequence([
        note(392.0, 0.22, 0.7),
        note(311.13, 0.22, 0.7),
        note(233.08, 0.45, 0.75),
    ]),

    # Ascending run into a held final chord for winning the campaign.
    "win": lambda: sequence([
        note(523.25, 0.12, 0.6),
        note(659.25, 0.12, 0.6),
        note(783.99, 0.12, 0.6),
        chord([note(1046.5, 0.5, 0.5),
               note(1318.5, 0.5, 0.4),
               note(1567.98, 0.5, 0.3)]),
    ]),
}


def main():
    random.seed(20261103)  # deterministic output
    for name, fn in SOUNDS.items():
        path, duration = write_wav(name, fn())
        print(f"  {os.path.basename(path):>14}  {duration:5.2f}s")
    print(f"\nWrote {len(SOUNDS)} sound effects to {OUT_DIR}")


if __name__ == "__main__":
    main()
