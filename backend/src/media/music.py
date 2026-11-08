"""Background music bed for rendered clips.

Tracks are royalty-free audio files dropped into ``backend/music``. The bed is
looped to the clip length, ducked under speech with a sidechain compressor and
faded in and out. Only the audio is re-encoded; the video stream is copied.
"""

import hashlib
from pathlib import Path
from typing import List, Optional

from .common import AUDIO_BITRATE, LOUDNORM_FILTER, logger
from .ffmpeg import ffprobe_duration, ffprobe_has_audio, run_ffmpeg_command

MUSIC_DIR = Path(__file__).resolve().parent.parent.parent / "music"
MUSIC_EXTENSIONS = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac", ".opus"}
FADE_IN_SECONDS = 1.0
FADE_OUT_SECONDS = 1.5


def list_music_tracks(music_dir: Path = MUSIC_DIR) -> List[Path]:
    """Audio files in the music folder, in a stable order."""
    if not music_dir.is_dir():
        return []
    return sorted(
        path for path in music_dir.iterdir()
        if path.is_file() and path.suffix.lower() in MUSIC_EXTENSIONS
    )


def pick_music_track(seed: str, music_dir: Path = MUSIC_DIR) -> Optional[Path]:
    """The track for a clip. The same seed always gets the same track."""
    tracks = list_music_tracks(music_dir)
    if not tracks:
        return None
    index = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16) % len(tracks)
    return tracks[index]


def music_bed_filter(duration: float, volume_db: float) -> str:
    """filter_complex mixing input 1 (looped music) under input 0 (speech) into [aout]."""
    fade_out_start = max(0.0, duration - FADE_OUT_SECONDS)
    return (
        f"[1:a]atrim=0:{duration:.3f},asetpts=PTS-STARTPTS,volume={volume_db}dB,"
        f"afade=t=in:d={FADE_IN_SECONDS},afade=t=out:st={fade_out_start:.3f}:d={FADE_OUT_SECONDS}[bed];"
        "[0:a]asplit=2[speech][key];"
        "[bed][key]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=350[ducked];"
        f"[speech][ducked]amix=inputs=2:duration=first:normalize=0,{LOUDNORM_FILTER}[aout]"
    )


def mix_background_music(video_path: Path, track_path: Path, output_path: Path, volume_db: float) -> bool:
    """Write ``video_path`` with ``track_path`` mixed under its speech to ``output_path``."""
    if not ffprobe_has_audio(video_path):
        logger.info("Skipping background music: %s has no audio", video_path.name)
        return False
    duration = ffprobe_duration(video_path)
    if not duration or duration <= 0:
        return False
    command = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(video_path),
        "-stream_loop", "-1", "-i", str(track_path),
        "-filter_complex", music_bed_filter(duration, volume_db),
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-ar", "48000",
        "-map_chapters", "-1",
        "-movflags", "+faststart",
        "-t", f"{duration:.3f}",
        str(output_path),
    ]
    result = run_ffmpeg_command(command)
    if result.returncode != 0:
        logger.warning("Background music mix failed: %s", result.stderr[-500:])
        output_path.unlink(missing_ok=True)
        return False
    logger.info("Mixed background music %s into %s", track_path.name, video_path.name)
    return True
