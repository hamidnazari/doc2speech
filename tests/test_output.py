from __future__ import annotations

import io
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from rich.console import Console

from readback.output import write_file, write_stdout


def test_write_file_uses_streaming_sentence_segments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    segments: list[str] = []
    written: list[tuple[str, int]] = []

    class FakeKokoro:
        def __init__(self, *_args: object) -> None:
            pass

        async def create_stream(self, segment: str, **_kwargs: object):
            segments.append(segment)
            yield np.array([float(len(segments))], dtype="float32"), 24_000

    def fake_write(output_path: str, samples: np.ndarray, sample_rate: int) -> None:
        written.append((output_path, sample_rate))
        assert samples.tolist() == [1.0, 2.0]

    monkeypatch.setitem(sys.modules, "kokoro_onnx", SimpleNamespace(Kokoro=FakeKokoro))
    monkeypatch.setattr("readback.synth.ensure_model", lambda: (tmp_path / "m", tmp_path / "v"))
    monkeypatch.setattr("soundfile.write", fake_write)

    text = "First sentence. " * 20
    write_file(text, "af_heart", 1.0, "out.wav", Console(file=io.StringIO()))

    assert len(segments) == 2
    assert written == [("out.wav", 24_000)]


class _Stdout:
    def __init__(self) -> None:
        self.buffer: io.BytesIO = io.BytesIO()


def test_write_stdout_uses_streaming_sentence_segments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    segments: list[str] = []
    stdout = _Stdout()

    class FakeKokoro:
        def __init__(self, *_args: object) -> None:
            pass

        async def create_stream(self, segment: str, **_kwargs: object):
            segments.append(segment)
            yield np.array([float(len(segments))], dtype="float32"), 24_000

    def fake_write(
        buf: io.BytesIO, samples: np.ndarray, sample_rate: int, **_kwargs: object
    ) -> None:
        assert sample_rate == 24_000
        assert samples.tolist() == [1.0, 2.0]
        _ = buf.write(b"wav-bytes")

    monkeypatch.setitem(sys.modules, "kokoro_onnx", SimpleNamespace(Kokoro=FakeKokoro))
    monkeypatch.setattr("readback.synth.ensure_model", lambda: (tmp_path / "m", tmp_path / "v"))
    monkeypatch.setattr("soundfile.write", fake_write)
    monkeypatch.setattr(sys, "stdout", stdout)

    text = "First sentence. " * 20
    write_stdout(text, "af_heart", 1.0, Console(file=io.StringIO()))

    assert len(segments) == 2
    assert stdout.buffer.getvalue() == b"wav-bytes"
