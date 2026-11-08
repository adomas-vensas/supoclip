"""Retention edits for vertical clips: punch-in zooms that change the frame every few seconds."""

from typing import Any, Dict, List, Optional, Tuple

from .timeline import word_ends_sentence

MIN_CHANGE_GAP_SECONDS = 2.5
FILL_CHANGE_AFTER_SECONDS = 4.0
PHRASE_PAUSE_SECONDS = 0.35
END_GUARD_SECONDS = 1.0
PUNCH_IN_ZOOM = 0.1


def _phrase_starts(words: List[Dict[str, Any]]) -> List[float]:
    """Start times of words that open a new sentence or follow a pause."""
    return [
        current["start"]
        for previous, current in zip(words, words[1:])
        if word_ends_sentence(previous["text"]) or current["start"] - previous["end"] >= PHRASE_PAUSE_SECONDS
    ]


def punch_in_change_times(words: List[Dict[str, Any]], duration: float) -> List[float]:
    """Times to toggle the zoom: on new phrases at least 2.5 s apart, or on any word once 4 s have passed."""
    last_allowed = duration - END_GUARD_SECONDS
    starts = [word["start"] for word in words if 0 < word["start"] < last_allowed]
    phrase_starts = set(_phrase_starts(words))
    changes: List[float] = []
    last_change = 0.0
    for start in starts:
        since_last = start - last_change
        if since_last < MIN_CHANGE_GAP_SECONDS:
            continue
        if start in phrase_starts or since_last >= FILL_CHANGE_AFTER_SECONDS:
            changes.append(start)
            last_change = start
    return changes


def punch_in_windows(words: List[Dict[str, Any]], duration: float) -> List[Tuple[float, float]]:
    """Intervals where the frame is zoomed in, alternating at each change time."""
    bounds = punch_in_change_times(words, duration) + [duration]
    return [(start, end) for start, end in zip(bounds[0::2], bounds[1::2]) if end > start]


def punch_in_filter(
    windows: List[Tuple[float, float]], width: int = 1080, height: int = 1920, zoom: float = PUNCH_IN_ZOOM
) -> Optional[str]:
    """ffmpeg filter that scales the frame up by ``zoom`` inside ``windows`` and crops back to size."""
    if not windows:
        return None
    active = "+".join(f"between(t,{start:.3f},{end:.3f})" for start, end in windows)
    factor = f"(1+{zoom}*min(1,{active}))"
    return (
        f"scale=w='trunc({width}*{factor}/2)*2':h='trunc({height}*{factor}/2)*2':eval=frame:flags=lanczos,"
        f"crop={width}:{height},setsar=1"
    )
