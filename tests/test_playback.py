from __future__ import annotations

import io
import sys
from types import SimpleNamespace
from typing import override

import numpy as np
import pytest

from readback.playback import play_stream


class _NonTty(io.StringIO):
    @override
    def isatty(self) -> bool:
        return False

    @override
    def fileno(self) -> int:
        raise AssertionError("non-interactive playback must not read terminal controls")


class _OutputStream:
    active: bool = False

    def __init__(self, **_kwargs: object) -> None:
        pass

    def __enter__(self) -> _OutputStream:
        return self

    def __exit__(self, *_args: object) -> None:
        pass


def test_play_stream_non_tty_skips_terminal_controls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_synthesise_stream(*_args: object, **_kwargs: object):
        yield np.zeros(4, dtype="float32"), 24_000

    monkeypatch.setattr(sys, "stdin", _NonTty(""))
    monkeypatch.setitem(
        sys.modules,
        "sounddevice",
        SimpleNamespace(OutputStream=_OutputStream, CallbackStop=RuntimeError),
    )
    monkeypatch.setattr("readback.synth.synthesise_stream", fake_synthesise_stream)

    play_stream("Hello world.", "af_heart", 1.0)
