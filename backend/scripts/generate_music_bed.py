"""Generate original, royalty-free background music beds for backend/music.

Everything is synthesized here, so the output carries no third-party rights.
The beds are deliberately plain (soft chords, bass, kick and hats) so they sit
under speech without competing with it.

    uv run python scripts/generate_music_bed.py            # three default beds
    uv run python scripts/generate_music_bed.py --bpm 92 --key 2 --seed 7 --name bed_d
"""

import argparse
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 44100
MUSIC_DIR = Path(__file__).resolve().parent.parent / "music"
# Minor-key loop i-VI-III-VII, as semitones above the key's A.
PROGRESSION = [(0, 3, 7), (-4, 0, 3), (3, 7, 10), (-2, 2, 5)]
DEFAULT_BEDS = [
    {"name": "supoclip_bed_lofi", "bpm": 84, "key": 0, "seed": 1},
    {"name": "supoclip_bed_drive", "bpm": 100, "key": 5, "seed": 2},
    {"name": "supoclip_bed_calm", "bpm": 72, "key": -3, "seed": 3},
]


def frequency(semitones_from_a3: float) -> float:
    return 220.0 * 2 ** (semitones_from_a3 / 12)


def envelope(length: int, attack: float, release: float) -> np.ndarray:
    attack_n = min(length, max(1, int(attack * SAMPLE_RATE)))
    release_n = min(length, max(1, int(release * SAMPLE_RATE)))
    shape = np.ones(length)
    shape[:attack_n] = np.linspace(0, 1, attack_n)
    shape[-release_n:] *= np.linspace(1, 0, release_n)
    return shape


def tone(freq: float, seconds: float, partials=(1.0, 0.35, 0.12)) -> np.ndarray:
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return sum(weight * np.sin(2 * np.pi * freq * (index + 1) * t) for index, weight in enumerate(partials))


def kick(seconds: float) -> np.ndarray:
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    sweep = 45 + 75 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(sweep) / SAMPLE_RATE) * np.exp(-t * 9)


def hat(seconds: float, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    noise = np.diff(rng.standard_normal(len(t) + 1))
    return noise * np.exp(-t * 60) * 0.25


def place(track: np.ndarray, sound: np.ndarray, start: float, gain: float) -> None:
    begin = int(start * SAMPLE_RATE)
    end = min(len(track), begin + len(sound))
    track[begin:end] += gain * sound[: end - begin]


def render_bed(bpm: float, key: int, seed: int, bars: int = 32) -> np.ndarray:
    rng = np.random.default_rng(seed)
    beat = 60.0 / bpm
    bar = 4 * beat
    track = np.zeros(int(bars * bar * SAMPLE_RATE) + SAMPLE_RATE)
    for bar_index in range(bars):
        chord = PROGRESSION[bar_index % len(PROGRESSION)]
        start = bar_index * bar
        pad = sum(tone(frequency(key + note), bar) for note in chord) / len(chord)
        place(track, pad * envelope(len(pad), 0.4, 0.6), start, 0.32)
        bass = tone(frequency(key + chord[0] - 12), bar * 0.9, partials=(1.0, 0.2))
        place(track, bass * envelope(len(bass), 0.02, 0.3), start, 0.38)
        arpeggio_notes = [chord[i % 3] + 12 * (i // 3) for i in rng.permutation(6)]
        for step, note in enumerate(arpeggio_notes[:4]):
            pluck = tone(frequency(key + note + 12), beat * 0.9, partials=(1.0, 0.25))
            place(track, pluck * np.exp(-np.arange(len(pluck)) / SAMPLE_RATE * 6), start + step * beat, 0.07)
        for beat_index in range(4):
            if beat_index in (0, 2):
                place(track, kick(0.5), start + beat_index * beat, 0.55)
            place(track, hat(0.08, rng), start + (beat_index + 0.5) * beat, 0.5)
    track += rng.standard_normal(len(track)) * 0.003
    return track / (np.max(np.abs(track)) or 1.0) * 0.8


def write_track(samples: np.ndarray, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp_dir:
        wav_path = Path(temp_dir) / "bed.wav"
        with wave.open(str(wav_path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(SAMPLE_RATE)
            handle.writeframes((samples * 32767).astype(np.int16).tobytes())
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error", "-i", str(wav_path),
                "-af", "lowpass=f=6000,aecho=0.8:0.6:60|120:0.25|0.15,loudnorm=I=-16:TP=-2",
                "-ac", "2", "-c:a", "aac", "-b:a", "160k", str(output),
            ],
            check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name")
    parser.add_argument("--bpm", type=float, default=84)
    parser.add_argument("--key", type=int, default=0, help="semitones above A")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--bars", type=int, default=32)
    parser.add_argument("--out-dir", type=Path, default=MUSIC_DIR)
    args = parser.parse_args()
    beds = [vars(args) | {"name": args.name}] if args.name else DEFAULT_BEDS
    for bed in beds:
        output = args.out_dir / f"{bed['name']}.m4a"
        write_track(render_bed(bed["bpm"], bed["key"], bed["seed"], args.bars), output)
        print(output)


if __name__ == "__main__":
    main()
