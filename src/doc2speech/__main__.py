from __future__ import annotations

import sys

import click
from rich.console import Console

console = Console(stderr=True)

_VOICES = [
    "af_heart",
    "af_bella",
    "af_nicole",
    "af_sarah",
    "af_sky",
    "am_adam",
    "am_michael",
    "bf_emma",
    "bf_isabella",
    "bm_george",
    "bm_lewis",
]


@click.command()
@click.version_option(package_name="doc2speech")
@click.argument("input_file", default="-", metavar="FILE")
@click.option(
    "-o", "--output", "output_path", default=None, metavar="FILE", help="Output WAV file."
)
@click.option(
    "--play",
    "play",
    is_flag=True,
    default=False,
    help="Stream audio to the default audio device as chunks are synthesised.",
)
@click.option(
    "--voice",
    default="af_heart",
    show_default=True,
    type=click.Choice(_VOICES, case_sensitive=False),
    help="Kokoro voice ID.",
)
@click.option(
    "--speed", default=1.0, show_default=True, type=float, help="Speech speed multiplier."
)
@click.option(
    "--no-strip-markdown",
    is_flag=True,
    default=False,
    help="Disable markdown stripping (pass raw text).",
)
def cli(
    input_file: str,
    output_path: str | None,
    play: bool,
    voice: str,
    speed: float,
    no_strip_markdown: bool,
) -> None:
    """Convert a text or markdown FILE to speech.

    Pass '-' or omit FILE to read from stdin.
    """
    from doc2speech.text import load, strip_markdown

    console.print(f"[bold cyan]doc2speech[/] loading {input_file!r}…")
    raw = load(input_file)

    text = raw if no_strip_markdown else strip_markdown(raw)
    if not text.strip():
        console.print("[red]Error:[/] no text to synthesise.")
        raise SystemExit(1)

    console.print(f"[dim]{len(text)} chars → voice=[bold]{voice}[/] speed={speed}[/]")

    if output_path:
        _write_file(text, voice, speed, output_path)
    elif play or sys.stdout.isatty():
        _play_stream(text, voice, speed)
    else:
        _write_stdout(text, voice, speed)


class _Player:
    """Buffers synthesised audio and serves it frame-by-frame to a sounddevice callback."""

    def __init__(self, seek_samples: int) -> None:
        import threading

        self.seek_samples = seek_samples
        self.chunks: list[object] = []  # list[np.ndarray]
        self.lock = threading.Lock()
        self.synthesis_done = threading.Event()
        self.paused = threading.Event()
        self.stopped = threading.Event()
        self.playhead = 0

    def push(self, chunk: object) -> None:
        import numpy as np

        with self.lock:
            self.chunks.append(chunk.astype("float32"))  # type: ignore[union-attr]

    def total(self) -> int:
        with self.lock:
            return sum(len(c) for c in self.chunks)  # type: ignore[arg-type]

    def read(self, start: int, n: int) -> object:
        import numpy as np

        out = np.zeros(n, dtype="float32")
        written = pos = 0
        with self.lock:
            for chunk in self.chunks:
                end = pos + len(chunk)  # type: ignore[arg-type]
                if end <= start:
                    pos = end
                    continue
                src = max(0, start - pos)
                take = min(len(chunk) - src, n - written)  # type: ignore[arg-type]
                out[written : written + take] = chunk[src : src + take]  # type: ignore[index]
                written += take
                pos = end
                if written >= n:
                    break
        return out

    def callback(self, outdata: object, frames: int, _time: object, _status: object) -> None:
        import sounddevice as sd
        import numpy as np

        outdata = outdata  # type: ignore[assignment]
        if self.stopped.is_set():
            outdata[:] = 0  # type: ignore[index]
            raise sd.CallbackStop()
        if self.paused.is_set():
            outdata[:] = 0  # type: ignore[index]
            return
        total = self.total()
        if self.playhead >= total:
            if self.synthesis_done.is_set():
                outdata[:] = 0  # type: ignore[index]
                raise sd.CallbackStop()
            outdata[:] = 0  # type: ignore[index]  # underrun — synthesis hasn't caught up yet
            return
        outdata[:, 0] = self.read(self.playhead, frames)  # type: ignore[index]
        self.playhead += frames

    def seek(self, delta: int) -> None:
        self.playhead = max(0, min(self.playhead + delta, self.total()))


def _play_stream(text: str, voice: str, speed: float) -> None:
    import asyncio
    import termios
    import threading
    import tty

    import sounddevice as sd

    from doc2speech.synth import SAMPLE_RATE, synthesise_stream

    player = _Player(seek_samples=5 * SAMPLE_RATE)

    def _raw_print(msg: str) -> None:
        sys.stderr.write(f"\r{msg}\r\n")
        sys.stderr.flush()

    def _keyreader() -> None:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while not player.stopped.is_set():
                ch = sys.stdin.read(1)
                if ch == " ":
                    if player.paused.is_set():
                        player.paused.clear()
                        _raw_print("▶ resumed")
                    else:
                        player.paused.set()
                        _raw_print("⏸ paused")
                elif ch == "\x1b":
                    nxt = sys.stdin.read(1)
                    if nxt == "[":
                        arrow = sys.stdin.read(1)
                        if arrow == "C":  # →
                            player.seek(+player.seek_samples)
                            _raw_print("⏩ +5s")
                        elif arrow == "D":  # ←
                            player.seek(-player.seek_samples)
                            _raw_print("⏪ -5s")
                elif ch in ("\x03", "\x04", "q"):
                    player.stopped.set()
                    break
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    console.print("[dim]Playing… (space=pause/resume  ←/→=seek 5s  q=quit)[/]")

    with sd.OutputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=player.callback
    ) as stream:
        key_thread = threading.Thread(target=_keyreader, daemon=True)
        key_thread.start()

        async def run() -> None:
            async for chunk, _ in synthesise_stream(text, voice=voice, speed=speed):
                player.push(chunk)
            player.synthesis_done.set()

        asyncio.run(run())
        stream.wait()


def _write_file(text: str, voice: str, speed: float, output_path: str) -> None:
    import soundfile as sf

    from doc2speech.synth import SAMPLE_RATE, synthesise

    console.print("[dim]Synthesising…[/]")
    samples = synthesise(text, voice=voice, speed=speed)
    sf.write(output_path, samples, SAMPLE_RATE)  # type: ignore[arg-type]
    console.print(f"[green]✓[/] Written to [bold]{output_path}[/]")


def _write_stdout(text: str, voice: str, speed: float) -> None:
    import io

    import soundfile as sf

    from doc2speech.synth import SAMPLE_RATE, synthesise

    console.print("[dim]Synthesising…[/]")
    samples = synthesise(text, voice=voice, speed=speed)
    buf = io.BytesIO()
    sf.write(buf, samples, SAMPLE_RATE, format="WAV")  # type: ignore[arg-type]
    _ = sys.stdout.buffer.write(buf.getvalue())


if __name__ == "__main__":
    cli()
