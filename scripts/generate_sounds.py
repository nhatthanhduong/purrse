"""Generate Purrse's small, dependency-free PCM sound asset set."""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path


RATE = 44_100
OUTPUT = Path(__file__).parents[1] / "src" / "purrse" / "assets" / "sounds"


def envelope(t: float, duration: float, attack: float = 0.008, release: float = 0.08) -> float:
    return min(1.0, t / attack) * min(1.0, (duration - t) / release)


def write(name: str, duration: float, sample_fn) -> None:
    samples = [sample_fn(i / RATE) for i in range(int(RATE * duration))]
    peak = max(abs(sample) for sample in samples) or 1
    gain = 0.78 * 32767 / peak
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUTPUT / f"{name}.wav"), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(b"".join(struct.pack("<h", int(max(-32767, min(32767, sample * gain)))) for sample in samples))


def click(t: float) -> float:
    duration = 0.105
    decay = math.exp(-t * 38)
    return envelope(t, duration, 0.002, 0.035) * decay * (math.sin(2 * math.pi * 920 * t) + 0.35 * math.sin(2 * math.pi * 1460 * t))


def pop(t: float) -> float:
    duration = 0.28
    frequency = 520 + 620 * (t / duration) ** 0.55
    bounce = math.sin(2 * math.pi * frequency * t) + 0.28 * math.sin(2 * math.pi * frequency * 2.01 * t)
    return envelope(t, duration, 0.006, 0.1) * math.exp(-t * 5.5) * bounce


def whoosh(t: float) -> float:
    duration = 0.34
    rng = random.Random(int(t * RATE) + 729)
    noise = rng.uniform(-1, 1)
    sweep = math.sin(2 * math.pi * (180 + 1100 * (t / duration) ** 2) * t)
    shape = math.sin(math.pi * t / duration) ** 1.7
    return shape * (0.36 * noise + 0.64 * sweep)


def celebrate(t: float) -> float:
    duration = 0.92
    notes = (523.25, 659.25, 783.99, 1046.5)
    segment = duration / len(notes)
    note_index = min(len(notes) - 1, int(t / segment))
    local = t - note_index * segment
    note_env = envelope(local, segment, 0.006, 0.11) * math.exp(-local * 2.4)
    frequency = notes[note_index]
    chime = math.sin(2 * math.pi * frequency * local) + 0.32 * math.sin(2 * math.pi * frequency * 2.01 * local) + 0.12 * math.sin(2 * math.pi * frequency * 3.98 * local)
    return note_env * chime


def meow(t: float) -> float:
    """A bright, small-cat meow: a voiced vowel with a falling pitch and soft onset."""
    duration = 0.72
    position = min(1.0, t / duration)
    frequency = 760 - 330 * position + 55 * math.sin(math.pi * position)
    phase = 2 * math.pi * frequency * t
    voiced = math.sin(phase) + 0.48 * math.sin(phase * 2) + 0.2 * math.sin(phase * 3)
    formant = 0.42 * math.sin(2 * math.pi * 1500 * t) + 0.16 * math.sin(2 * math.pi * 2450 * t)
    vibrato = 1 + 0.07 * math.sin(2 * math.pi * 8 * t)
    shape = envelope(t, duration, 0.035, 0.18) * (0.72 + 0.28 * math.sin(math.pi * position))
    return shape * vibrato * (voiced + formant)


if __name__ == "__main__":
    write("click", 0.105, click)
    write("pop", 0.28, pop)
    write("whoosh", 0.34, whoosh)
    write("celebrate", 0.92, celebrate)
    write("meow", 0.72, meow)
    print(f"Generated 5 sound assets in {OUTPUT}")
