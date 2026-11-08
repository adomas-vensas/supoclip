# Background music

Audio files here (`.mp3`, `.m4a`, `.aac`, `.wav`, `.ogg`, `.flac`, `.opus`) are mixed under generated
clips when `BACKGROUND_MUSIC=true`. Each clip gets one track, picked by its file name, looped to the
clip length, faded in and out, and ducked under speech. `BACKGROUND_MUSIC_DB` (default `-20`) sets the
track level before ducking.

Only add music you are allowed to publish on every platform you post to:

- `uv run python scripts/generate_music_bed.py` writes three original beds made by code, with no
  third-party rights.
- The YouTube Audio Library is copyright-safe on YouTube. Check each track's license before using it
  on TikTok or Instagram, and credit Creative Commons tracks in the description.
- Pixabay Music is free without attribution, but its license forbids redistributing the files on
  their own, so do not commit them to a public repository.

Skip music on clips whose source already has music, and on campaigns that forbid added audio.
