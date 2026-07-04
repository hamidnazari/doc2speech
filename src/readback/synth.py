from __future__ import annotations

import hashlib
import os
import tempfile
import urllib.error
import urllib.request
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    import numpy as np

# Model is downloaded once to ~/.cache/kokoro on first use
_MODEL_PATH = Path.home() / ".cache" / "kokoro" / "kokoro-v1.0.onnx"
_VOICES_PATH = Path.home() / ".cache" / "kokoro" / "voices-v1.0.bin"
_MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
_VOICES_URL = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
)
_MODEL_SHA256 = "7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5"
_VOICES_SHA256 = "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"

SAMPLE_RATE = 24_000


@dataclass(frozen=True)
class _ModelFile:
    path: Path
    url: str
    sha256: str


def _model_files() -> tuple[_ModelFile, _ModelFile]:
    return (
        _ModelFile(_MODEL_PATH, _MODEL_URL, _MODEL_SHA256),
        _ModelFile(_VOICES_PATH, _VOICES_URL, _VOICES_SHA256),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _has_expected_checksum(path: Path, expected_sha256: str) -> bool:
    try:
        return _sha256(path) == expected_sha256
    except OSError as e:
        raise click.ClickException(f"Failed to read cached model file {path}: {e}") from e


def _download_model_file(model_file: _ModelFile) -> None:
    path = model_file.path
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        fd, temp_name = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", suffix=".download"
        )
        os.close(fd)
    except OSError as e:
        raise click.ClickException(f"Failed to create temporary model file for {path}: {e}") from e

    temp_path = Path(temp_name)
    try:
        _ = urllib.request.urlretrieve(model_file.url, temp_path)
        actual_sha256 = _sha256(temp_path)
        if actual_sha256 != model_file.sha256:
            message = (
                f"Downloaded model file {path.name} failed checksum verification: "
                f"expected {model_file.sha256}, got {actual_sha256}"
            )
            raise click.ClickException(message)
        os.replace(temp_path, path)
    except click.ClickException:
        raise
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        raise click.ClickException(f"Failed to download model file {path.name}: {reason}") from e
    except OSError as e:
        raise click.ClickException(f"Failed to save model file to {path}: {e}") from e
    finally:
        with suppress(OSError):
            temp_path.unlink(missing_ok=True)


def ensure_model() -> tuple[Path, Path]:
    """Download Kokoro model files if not already cached."""
    for model_file in _model_files():
        if model_file.path.exists() and _has_expected_checksum(model_file.path, model_file.sha256):
            continue
        _download_model_file(model_file)

    return _MODEL_PATH, _VOICES_PATH


async def synthesise_stream(
    text: str, voice: str = "af_heart", speed: float = 1.0
) -> AsyncGenerator[tuple[np.ndarray, int]]:
    """Yield (chunk, sample_rate) as each phoneme batch is synthesised."""
    from kokoro_onnx import Kokoro

    from readback.text import split_sentences

    model_path, voices_path = ensure_model()
    kokoro = Kokoro(str(model_path), str(voices_path))
    for segment in split_sentences(text):
        async for chunk, sr in kokoro.create_stream(
            segment, voice=voice, speed=speed, lang="en-us"
        ):
            yield chunk, sr


def synthesise(text: str, voice: str = "af_heart", speed: float = 1.0) -> np.ndarray:
    """Return a float32 audio array at 24 kHz."""
    from kokoro_onnx import Kokoro

    model_path, voices_path = ensure_model()
    kokoro = Kokoro(str(model_path), str(voices_path))
    samples, _sr = kokoro.create(text, voice=voice, speed=speed, lang="en-us")
    return samples
