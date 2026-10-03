import math
import struct
import wave
from pathlib import Path


def test_bundled_sound_assets_are_audible_pcm():
    sound_dir = Path(__file__).parents[1] / "src" / "purrse" / "assets" / "sounds"
    expected = {"click.wav", "pop.wav", "whoosh.wav", "celebrate.wav", "meow.wav"}
    assert {path.name for path in sound_dir.glob("*.wav")} == expected
    for path in sound_dir.glob("*.wav"):
        with wave.open(str(path), "rb") as sound:
            assert sound.getnchannels() == 1
            assert sound.getframerate() == 44_100
            raw = sound.readframes(sound.getnframes())
            samples = struct.unpack("<" + "h" * (len(raw) // 2), raw)
            rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
            assert max(abs(sample) for sample in samples) > 24_000
            assert rms > 5_000
