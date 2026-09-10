#!/usr/bin/env python3
"""Generate POPR's three notification sounds: low, warm, and related.

macOS ships fourteen system sounds and every one of them is a chime or an alert.
These are swells instead, deep enough to register without being a ping. All
three share a timbre so they read as one instrument, and differ in harmony so
you can tell them apart without looking:

    pop.wav   a turn finished     G major, settled
    ask.wav   Claude needs you    rises a tone, open, asks a question
    err.wav   the turn broke      minor, falls, does not resolve

Standard library only, so they regenerate anywhere.

    python3 assets/make_sound.py
"""

import array
import math
import pathlib
import wave

HERE = pathlib.Path(__file__).parent
RATE = 44100
DETUNE = 0.35  # Hz, a second layer slightly off to make it breathe

# Each voice is (frequency, gain, delay, decay). Low fundamental for body, the
# upper partials quiet and late so the sound blooms open rather than arriving
# all at once.
SOUNDS = {
    # G major, settled. Nothing left to ask.
    "pop": (1.10, [
        (98.00, 0.55, 0.000, 0.42),   # G2, the hum itself
        (146.83, 0.30, 0.020, 0.38),  # D3, the fifth
        (196.00, 0.20, 0.045, 0.32),  # G3, octave, adds the shine
        (293.66, 0.07, 0.070, 0.22),  # D4, a whisper of air
    ]),
    # Rises a tone partway through, which is what makes it read as a question.
    "ask": (1.00, [
        (98.00, 0.42, 0.000, 0.30),
        (146.83, 0.26, 0.015, 0.28),
        (196.00, 0.20, 0.180, 0.34),  # the lift, entering late
        (220.00, 0.16, 0.200, 0.32),  # A3 over the G, unresolved on purpose
    ]),
    # Minor and falling. Lands lower than it started.
    "err": (1.15, [
        (98.00, 0.50, 0.000, 0.34),
        (116.54, 0.30, 0.010, 0.32),  # Bb2, the minor third
        (87.31, 0.34, 0.170, 0.45),   # F2, drops below the root
        (174.61, 0.10, 0.180, 0.26),
    ]),
}


def envelope(t, delay, decay):
    """Soft attack then exponential decay. No clicks at either end."""
    if t < delay:
        return 0.0
    u = t - delay
    attack = min(1.0, u / 0.012)
    return attack * math.exp(-u / decay)


def render(length, voices):
    n = int(RATE * length)
    buf = array.array("h", bytes(2 * n))
    for i in range(n):
        t = i / RATE
        s = 0.0
        for freq, gain, delay, decay in voices:
            e = envelope(t, delay, decay)
            if e <= 0.0:
                continue
            s += gain * e * (math.sin(2 * math.pi * freq * t)
                             + math.sin(2 * math.pi * (freq + DETUNE) * t)) / 2
        # a hair of soft clipping, which rounds the peak instead of squaring it
        s = math.tanh(s * 1.25) * 0.72
        # fade the last 120ms to true silence so it never cuts
        tail = length - t
        if tail < 0.12:
            s *= tail / 0.12
        buf[i] = int(max(-1.0, min(1.0, s)) * 32767)
    return buf


def main():
    for name, (length, voices) in SOUNDS.items():
        out = HERE / f"{name}.wav"
        with wave.open(str(out), "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(render(length, voices).tobytes())
        print(f"assets/{name}.wav  {out.stat().st_size} bytes, {length}s")


def demo():
    for name, (length, voices) in SOUNDS.items():
        buf = render(length, voices)
        assert len(buf) == int(RATE * length), name
        assert buf[0] == 0, (name, buf[0])              # starts from silence
        assert abs(buf[-1]) < 100, (name, buf[-1])      # and ends there
        peak = max(abs(v) for v in buf)
        assert 12000 < peak < 32767, (name, peak)       # audible, never clipped
        mid = abs(buf[int(RATE * length * 0.8)])
        assert mid < peak, (name, mid, peak)            # decays rather than sustains
        print(f"  {name}: ok, peak {peak}")
    print("demo ok")


if __name__ == "__main__":
    import sys
    demo() if "--demo" in sys.argv else main()
