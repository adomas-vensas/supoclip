import shutil
import subprocess
from pathlib import Path

import pytest

from src.media import music
from src.media.ffmpeg import ffprobe_duration

needs_ffmpeg = pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="ffmpeg required"
)


def _write(path: Path, *lavfi: str) -> Path:
    inputs = [arg for source in lavfi for arg in ("-f", "lavfi", "-i", source)]
    codecs = ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"] if path.suffix == ".mp4" else []
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, *codecs, "-c:a", "aac", "-shortest", str(path)], check=True)
    return path


def test_tracks_ignore_other_files(tmp_path):
    for name in ("b.mp3", "a.m4a", "README.md", "cover.jpg"):
        (tmp_path / name).write_bytes(b"")

    assert [p.name for p in music.list_music_tracks(tmp_path)] == ["a.m4a", "b.mp3"]


def test_pick_is_stable_and_empty_folder_has_none(tmp_path):
    assert music.pick_music_track("clip.mp4", tmp_path) is None
    for name in ("a.mp3", "b.mp3", "c.mp3"):
        (tmp_path / name).write_bytes(b"")

    picks = {music.pick_music_track(f"clip_{i}.mp4", tmp_path) for i in range(30)}

    assert music.pick_music_track("clip_1.mp4", tmp_path) == music.pick_music_track("clip_1.mp4", tmp_path)
    assert len(picks) > 1


def test_filter_fades_out_before_the_end():
    graph = music.music_bed_filter(30.0, -20.0)

    assert "volume=-20.0dB" in graph
    assert "afade=t=out:st=28.500" in graph
    assert "sidechaincompress" in graph
    assert graph.endswith("[aout]")


@needs_ffmpeg
def test_mix_keeps_video_and_clip_length(tmp_path):
    clip = _write(tmp_path / "clip.mp4", "testsrc=s=320x240:r=30:d=6", "sine=f=220:d=6")
    track = _write(tmp_path / "bed.m4a", "sine=f=440:d=2")
    output = tmp_path / "scored.mp4"

    assert music.mix_background_music(clip, track, output, -20.0)
    assert abs(ffprobe_duration(output) - ffprobe_duration(clip)) < 0.1


@needs_ffmpeg
def test_mix_skips_silent_clip(tmp_path):
    clip = tmp_path / "silent.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=320x240:r=30:d=2",
         "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(clip)],
        check=True,
    )
    track = _write(tmp_path / "bed.m4a", "sine=f=440:d=2")

    assert not music.mix_background_music(clip, track, tmp_path / "out.mp4", -20.0)
