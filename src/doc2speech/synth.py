from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    import numpy as np

# Model is downloaded once to ~/.cache/kokoro on first use
_MODEL_PATH = Path.home() / ".cache" / "kokoro" / "kokoro-v1.0.onnx"
_VOICES_PATH = Path.home() / ".cache" / "kokoro" / "voices-v1.0.bin"

SAMPLE_RATE = 24_000


def ensure_model() -> tuple[Path, Path]:
    """Download Kokoro model files if not already cached."""
    import urllib.request

    _MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    files = {
        _MODEL_PATH: "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
        _VOICES_PATH: "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
    }
    for dest, url in files.items():
        if not dest.exists():
            _ = urllib.request.urlretrieve(url, dest)

    return _MODEL_PATH, _VOICES_PATH


async def synthesise_stream(
    text: str, voice: str = "af_heart", speed: float = 1.0
) -> AsyncGenerator[tuple[np.ndarray, int], None]:
    """Yield (chunk, sample_rate) as each phoneme batch is synthesised."""
    from kokoro_onnx import Kokoro

    from doc2speech.text import split_sentences

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
