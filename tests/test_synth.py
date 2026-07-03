from __future__ import annotations

import hashlib
import urllib.error
from pathlib import Path

import click
import pytest

from readback import synth


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@pytest.fixture
def model_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    model_path = tmp_path / "kokoro-v1.0.onnx"
    voices_path = tmp_path / "voices-v1.0.bin"
    monkeypatch.setattr(synth, "_MODEL_PATH", model_path)
    monkeypatch.setattr(synth, "_VOICES_PATH", voices_path)
    return model_path, voices_path


def test_ensure_model_reuses_valid_cached_files(
    monkeypatch: pytest.MonkeyPatch, model_files: tuple[Path, Path]
) -> None:
    model_path, voices_path = model_files
    model_content = b"valid model"
    voices_content = b"valid voices"
    _ = model_path.write_bytes(model_content)
    _ = voices_path.write_bytes(voices_content)
    monkeypatch.setattr(synth, "_MODEL_SHA256", _sha256(model_content))
    monkeypatch.setattr(synth, "_VOICES_SHA256", _sha256(voices_content))

    def fail_download(url: str, filename: str | Path) -> None:
        raise AssertionError(f"unexpected download of {url} to {filename}")

    monkeypatch.setattr("readback.synth.urllib.request.urlretrieve", fail_download)

    assert synth.ensure_model() == (model_path, voices_path)


def test_ensure_model_redownloads_corrupted_existing_file(
    monkeypatch: pytest.MonkeyPatch, model_files: tuple[Path, Path]
) -> None:
    model_path, voices_path = model_files
    _ = model_path.write_bytes(b"corrupt model")
    voices_content = b"valid voices"
    _ = voices_path.write_bytes(voices_content)
    replacement_content = b"replacement model"
    monkeypatch.setattr(synth, "_MODEL_SHA256", _sha256(replacement_content))
    monkeypatch.setattr(synth, "_VOICES_SHA256", _sha256(voices_content))
    downloads: list[Path] = []

    def fake_download(_url: str, filename: str | Path) -> None:
        download_path = Path(filename)
        downloads.append(download_path)
        _ = download_path.write_bytes(replacement_content)

    monkeypatch.setattr("readback.synth.urllib.request.urlretrieve", fake_download)

    assert synth.ensure_model() == (model_path, voices_path)
    assert model_path.read_bytes() == replacement_content
    assert voices_path.read_bytes() == voices_content
    assert len(downloads) == 1
    assert downloads[0].parent == model_path.parent
    assert downloads[0] != model_path
    assert not downloads[0].exists()


def test_ensure_model_rejects_download_with_wrong_checksum(
    monkeypatch: pytest.MonkeyPatch, model_files: tuple[Path, Path]
) -> None:
    model_path, _voices_path = model_files
    monkeypatch.setattr(synth, "_MODEL_SHA256", _sha256(b"expected model"))

    def fake_download(_url: str, filename: str | Path) -> None:
        _ = Path(filename).write_bytes(b"wrong model")

    monkeypatch.setattr("readback.synth.urllib.request.urlretrieve", fake_download)

    with pytest.raises(click.ClickException, match="failed checksum verification"):
        _ = synth.ensure_model()

    assert not model_path.exists()
    assert list(model_path.parent.glob("*.download")) == []


def test_ensure_model_wraps_download_failures(
    monkeypatch: pytest.MonkeyPatch, model_files: tuple[Path, Path]
) -> None:
    model_path, _voices_path = model_files
    monkeypatch.setattr(synth, "_MODEL_SHA256", _sha256(b"expected model"))

    def fail_download(_url: str, _filename: str | Path) -> None:
        raise urllib.error.URLError("network unavailable")

    monkeypatch.setattr("readback.synth.urllib.request.urlretrieve", fail_download)

    with pytest.raises(click.ClickException, match="Failed to download model file"):
        _ = synth.ensure_model()

    assert not model_path.exists()
