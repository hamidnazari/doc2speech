from __future__ import annotations

import threading

import numpy as np
import pytest

from doc2speech.__main__ import _Player  # pyright: ignore[reportPrivateUsage]

SEEK = 100


def _make(samples: list[int]) -> _Player:
    """Return a _Player pre-loaded with chunks of the given lengths (values = index)."""
    p = _Player(seek_samples=SEEK)
    for i, n in enumerate(samples):
        p.push(np.full(n, float(i), dtype="float32"))
    return p


def _all(arr: np.ndarray, val: float) -> bool:
    """Check every element equals val without touching np.all (stubs return Any)."""
    flat: list[float] = arr.flatten().tolist()
    return flat == [val] * len(flat)


# ---------------------------------------------------------------------------
# _Player.total
# ---------------------------------------------------------------------------


def test_total_empty() -> None:
    p = _Player(seek_samples=SEEK)
    assert p.total() == 0


def test_total_single_chunk() -> None:
    p = _make([50])
    assert p.total() == 50


def test_total_multiple_chunks() -> None:
    p = _make([30, 40, 30])
    assert p.total() == 100


# ---------------------------------------------------------------------------
# _Player.read
# ---------------------------------------------------------------------------


def test_read_full_single_chunk() -> None:
    p = _make([8])
    out = p.read(0, 8)
    assert _all(out, 0.0)


def test_read_partial_start() -> None:
    p = _make([10])
    out = p.read(3, 4)
    assert len(out) == 4
    assert _all(out, 0.0)


def test_read_across_chunk_boundary() -> None:
    p = _Player(seek_samples=SEEK)
    p.push(np.ones(5, dtype="float32"))
    p.push(np.full(5, 2.0, dtype="float32"))
    out = p.read(3, 6)
    assert out.tolist() == [1.0, 1.0, 2.0, 2.0, 2.0, 2.0]


def test_read_past_end_zero_pads() -> None:
    p = _make([5])
    out = p.read(3, 10)
    assert len(out) == 10
    assert _all(out[5:], 0.0)


def test_read_entirely_before_start_returns_zeros() -> None:
    p = _make([5])
    out = p.read(10, 4)
    assert _all(out, 0.0)


# ---------------------------------------------------------------------------
# _Player.seek
# ---------------------------------------------------------------------------


def test_seek_forward() -> None:
    p = _make([200])
    p.playhead = 50
    p.seek(+SEEK)
    assert p.playhead == 150


def test_seek_backward() -> None:
    p = _make([200])
    p.playhead = 80
    p.seek(-SEEK)
    assert p.playhead == 0


def test_seek_clamps_to_zero() -> None:
    p = _make([200])
    p.playhead = 10
    p.seek(-SEEK)
    assert p.playhead == 0


def test_seek_clamps_to_total() -> None:
    p = _make([200])
    p.playhead = 180
    p.seek(+SEEK)
    assert p.playhead == 200


# ---------------------------------------------------------------------------
# _Player.callback
# ---------------------------------------------------------------------------


def _outdata(frames: int) -> np.ndarray:
    return np.zeros((frames, 1), dtype="float32")


def test_callback_outputs_audio() -> None:
    p = _Player(seek_samples=SEEK)
    p.push(np.ones(64, dtype="float32"))
    out = _outdata(16)
    p.callback(out, 16, None, None)
    assert _all(out[:, 0], 1.0)
    assert p.playhead == 16


def test_callback_paused_outputs_silence() -> None:
    p = _Player(seek_samples=SEEK)
    p.push(np.ones(64, dtype="float32"))
    p.paused.set()
    out = _outdata(16)
    out[:] = 9.0
    p.callback(out, 16, None, None)
    assert _all(out, 0.0)
    assert p.playhead == 0  # playhead must not advance while paused


def test_callback_stopped_raises() -> None:
    import sounddevice as sd

    p = _make([64])
    p.stopped.set()
    out = _outdata(16)
    with pytest.raises(sd.CallbackStop):
        p.callback(out, 16, None, None)


def test_callback_underrun_outputs_silence() -> None:
    p = _Player(seek_samples=SEEK)
    # no chunks pushed yet, synthesis not done → underrun
    out = _outdata(16)
    out[:] = 9.0
    p.callback(out, 16, None, None)
    assert _all(out, 0.0)
    assert p.playhead == 0


def test_callback_end_of_stream_raises() -> None:
    import sounddevice as sd

    p = _make([16])
    p.synthesis_done.set()
    p.playhead = 16  # already at end
    out = _outdata(16)
    with pytest.raises(sd.CallbackStop):
        p.callback(out, 16, None, None)


def test_callback_advances_playhead_correctly() -> None:
    p = _Player(seek_samples=SEEK)
    p.push(np.arange(64, dtype="float32"))
    out = _outdata(16)
    p.callback(out, 16, None, None)
    assert p.playhead == 16
    p.callback(out, 16, None, None)
    assert p.playhead == 32


# ---------------------------------------------------------------------------
# pause / resume toggle
# ---------------------------------------------------------------------------


def test_pause_then_resume() -> None:
    p = _make([64])
    assert not p.paused.is_set()
    p.paused.set()
    assert p.paused.is_set()
    p.paused.clear()
    assert not p.paused.is_set()


# ---------------------------------------------------------------------------
# thread safety: push while reading
# ---------------------------------------------------------------------------


def test_push_concurrent_with_read() -> None:
    p = _Player(seek_samples=SEEK)
    p.push(np.ones(1000, dtype="float32"))
    errors: list[Exception] = []

    def pusher() -> None:
        for _ in range(50):
            p.push(np.ones(100, dtype="float32"))

    def reader() -> None:
        try:
            for i in range(50):
                _ = p.read(i * 10, 32)
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=pusher)
    t2 = threading.Thread(target=reader)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert not errors
