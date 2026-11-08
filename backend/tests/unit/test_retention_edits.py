from src.media.retention import punch_in_change_times, punch_in_filter, punch_in_windows


def _words(*items):
    return [{"text": text, "start": start, "end": start + 0.3} for text, start in items]


SPEECH = _words(
    ("This", 0.2), ("is", 0.6), ("first.", 1.0),
    ("Second", 1.5), ("sentence", 2.0), ("goes", 2.6), ("here.", 3.0),
    ("Third", 3.5), ("one", 4.0), ("runs", 5.0), ("on", 6.0), ("and", 7.0), ("on", 8.0), ("forever", 9.0),
    ("End.", 12.0),
)


def test_changes_land_on_phrases_and_keep_their_spacing():
    changes = punch_in_change_times(SPEECH, 14.0)

    assert changes[0] == 3.5
    assert all(later - earlier >= 2.5 for earlier, later in zip(changes, changes[1:]))
    assert all(later - earlier <= 6.0 for earlier, later in zip([0.0, *changes], [*changes, 13.0]))


def test_no_change_in_the_last_second():
    assert all(change < 13.0 for change in punch_in_change_times(SPEECH, 14.0))


def test_windows_alternate_and_reach_the_end():
    changes = punch_in_change_times(SPEECH, 14.0)
    windows = punch_in_windows(SPEECH, 14.0)

    assert windows[0] == (changes[0], changes[1])
    assert all(end > start for start, end in windows)


def test_no_words_means_no_filter():
    assert punch_in_windows([], 10.0) == []
    assert punch_in_filter([]) is None


def test_filter_scales_inside_windows_and_crops_back():
    graph = punch_in_filter([(1.0, 2.5), (5.0, 7.0)])

    assert "between(t,1.000,2.500)+between(t,5.000,7.000)" in graph
    assert "eval=frame" in graph
    assert "crop=1080:1920" in graph
