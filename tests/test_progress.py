from __future__ import annotations

from readback.playback import fmt_time, render_bar

SR = 24_000  # matches SAMPLE_RATE


# ---------------------------------------------------------------------------
# fmt_time
# ---------------------------------------------------------------------------


def test_fmt_time_zero() -> None:
    assert fmt_time(0, SR) == "0:00"


def test_fmt_time_sub_minute() -> None:
    assert fmt_time(30 * SR, SR) == "0:30"


def test_fmt_time_exact_minute() -> None:
    assert fmt_time(60 * SR, SR) == "1:00"


def test_fmt_time_pads_seconds() -> None:
    assert fmt_time(65 * SR, SR) == "1:05"


def test_fmt_time_large_value() -> None:
    assert fmt_time(3661 * SR, SR) == "61:01"


def test_fmt_time_truncates_sub_second() -> None:
    # Partial second samples are truncated, not rounded
    assert fmt_time(SR - 1, SR) == "0:00"


# ---------------------------------------------------------------------------
# render_bar
# ---------------------------------------------------------------------------

WIDTH = 10


def test_render_bar_empty_total_all_unfilled() -> None:
    bar = render_bar(0, 0, True, SR, width=WIDTH)
    assert "░" * WIDTH in bar
    assert "█" not in bar


def test_render_bar_fully_played() -> None:
    bar = render_bar(60 * SR, 60 * SR, True, SR, width=WIDTH)
    assert "█" * WIDTH in bar
    assert "░" not in bar


def test_render_bar_halfway() -> None:
    bar = render_bar(30 * SR, 60 * SR, True, SR, width=WIDTH)
    assert "█" * 5 in bar
    assert "░" * 5 in bar


def test_render_bar_synth_in_progress_shows_tilde() -> None:
    bar = render_bar(0, 60 * SR, False, SR, width=WIDTH)
    assert "~" in bar


def test_render_bar_synth_done_no_tilde() -> None:
    bar = render_bar(0, 60 * SR, True, SR, width=WIDTH)
    assert "~" not in bar


def test_render_bar_action_shown() -> None:
    bar = render_bar(0, 60 * SR, True, SR, width=WIDTH, action="+5s")
    assert "+5s" in bar


def test_render_bar_no_action_no_label() -> None:
    bar = render_bar(0, 60 * SR, True, SR, width=WIDTH, action="")
    assert "+5s" not in bar
    assert "-5s" not in bar


def test_render_bar_resets_ansi_and_carriage_return() -> None:
    bar = render_bar(0, 60 * SR, True, SR, width=WIDTH)
    assert bar.startswith("\033[0m\r")


def test_render_bar_shows_playhead_time() -> None:
    bar = render_bar(90 * SR, 180 * SR, True, SR, width=WIDTH)
    assert "1:30" in bar


def test_render_bar_shows_total_time() -> None:
    bar = render_bar(0, 120 * SR, True, SR, width=WIDTH)
    assert "2:00" in bar


def test_render_bar_playhead_capped_at_total() -> None:
    # playhead beyond total should not overflow bar
    bar = render_bar(200 * SR, 60 * SR, True, SR, width=WIDTH)
    assert "█" * WIDTH in bar
    assert "░" not in bar


def test_render_bar_width_respected() -> None:
    for w in (5, 20, 80):
        bar = render_bar(0, 60 * SR, True, SR, width=w)
        filled = bar.count("█")
        unfilled = bar.count("░")
        assert filled + unfilled == w


def test_render_bar_shows_speed() -> None:
    bar = render_bar(0, 60 * SR, True, SR, width=WIDTH, speed=1.25)
    assert "1.25x" in bar
