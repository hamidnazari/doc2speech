from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from rich.console import Console


def write_file(text: str, voice: str, speed: float, output_path: str, console: Console) -> None:
    import asyncio

    import soundfile as sf

    from readback.synth import SAMPLE_RATE

    console.print("[dim]Synthesising…[/]")
    samples = asyncio.run(collect_samples(text, voice=voice, speed=speed))
    sf.write(output_path, samples, SAMPLE_RATE)  # type: ignore[arg-type]
    console.print(f"[green]✓[/] Written to [bold]{output_path}[/]")


def write_stdout(text: str, voice: str, speed: float, console: Console) -> None:
    import asyncio
    import io

    import soundfile as sf

    from readback.synth import SAMPLE_RATE

    console.print("[dim]Synthesising…[/]")
    samples = asyncio.run(collect_samples(text, voice=voice, speed=speed))
    buf = io.BytesIO()
    sf.write(buf, samples, SAMPLE_RATE, format="WAV")  # type: ignore[arg-type]
    _ = sys.stdout.buffer.write(buf.getvalue())


async def collect_samples(text: str, voice: str, speed: float) -> np.ndarray:
    import numpy as np

    from readback.synth import synthesise_stream

    chunks: list[np.ndarray] = []
    async for chunk, _sample_rate in synthesise_stream(text, voice=voice, speed=speed):
        chunks.append(chunk.astype("float32"))
    if not chunks:
        return np.array([], dtype="float32")
    return np.concatenate(chunks)
