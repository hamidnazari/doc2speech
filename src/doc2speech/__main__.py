from __future__ import annotations

import sys
import threading
from typing import TYPE_CHECKING

import click
from rich.console import Console

if TYPE_CHECKING:
    import numpy as np

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

    if output_path:
        _write_file(text, voice, speed, output_path)
    elif play or sys.stdout.isatty():
        console.print(f"[dim]{len(text)} chars → voice=[bold]{voice}[/bold] speed={speed}[/dim]")
        console.file.write("\033[0m")
        console.file.flush()
        _play_stream(text, voice, speed)
    else:
        _write_stdout(text, voice, speed)


class _Player:
    """Buffers synthesised audio and serves it frame-by-frame to a sounddevice callback."""

    seek_samples: int
    chunks: list[np.ndarray]
    lock: threading.Lock
    synthesis_done: threading.Event
    paused: threading.Event
    stopped: threading.Event
    playhead: int

    def __init__(self, seek_samples: int) -> None:
        self.seek_samples = seek_samples
        self.chunks = []
        self.lock = threading.Lock()
        self.synthesis_done = threading.Event()
        self.paused = threading.Event()
        self.stopped = threading.Event()
        self.playhead = 0

    def push(self, chunk: np.ndarray) -> None:
        with self.lock:
            self.chunks.append(chunk.astype("float32"))

    def total(self) -> int:
        with self.lock:
            return sum(len(c) for c in self.chunks)

    def read(self, start: int, n: int) -> np.ndarray:
        import numpy as np

        out = np.zeros(n, dtype="float32")
        written = pos = 0
        with self.lock:
            for chunk in self.chunks:
                end = pos + len(chunk)
                if end <= start:
                    pos = end
                    continue
                src = max(0, start - pos)
                take = min(len(chunk) - src, n - written)
                out[written : written + take] = chunk[src : src + take]
                written += take
                pos = end
                if written >= n:
                    break
        return out

    def callback(
        self,
        outdata: np.ndarray,
        frames: int,
        _time: object,
        _status: object,
    ) -> None:
        import sounddevice as sd

        if self.stopped.is_set():
            outdata[:] = 0
            raise sd.CallbackStop()
        if self.paused.is_set():
            outdata[:] = 0
            return
        total = self.total()
        if self.playhead >= total:
            if self.synthesis_done.is_set():
                outdata[:] = 0
                raise sd.CallbackStop()
            outdata[:] = 0  # underrun — synthesis hasn't caught up yet
            return
        outdata[:, 0] = self.read(self.playhead, frames)
        self.playhead += frames

    def seek(self, delta: int) -> None:
        self.playhead = max(0, min(self.playhead + delta, self.total()))


def _fmt_time(samples: int, sample_rate: int) -> str:
    secs = samples // sample_rate
    return f"{secs // 60}:{secs % 60:02d}"


def _render_bar(
    playhead: int,
    total: int,
    synth_done: bool,
    sample_rate: int,
    width: int = 40,
    action: str = "",
) -> str:
    filled = 0 if total == 0 else int(min(playhead / total, 1.0) * width)
    bar = "█" * filled + ("░" * (width - filled))
    total_str = _fmt_time(total, sample_rate) if synth_done else f"~{_fmt_time(total, sample_rate)}"
    action_col = f"  {action:<6}" if action else " " * 8
    return f"\033[0m\r{_fmt_time(playhead, sample_rate)} [{bar}] {total_str}{action_col}"


def _play_stream(text: str, voice: str, speed: float) -> None:
    import asyncio
    import termios
    import tty

    import sounddevice as sd

    from doc2speech.synth import SAMPLE_RATE, synthesise_stream

    player = _Player(seek_samples=5 * SAMPLE_RATE)
    done = threading.Event()
    _action: list[str] = [""]  # shared mutable cell for current action label

    def _keyreader() -> None:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            _ = tty.setraw(fd)
            while not player.stopped.is_set() and not done.is_set():
                ch = sys.stdin.read(1)
                if ch == " ":
                    if player.paused.is_set():
                        player.paused.clear()
                        _action[0] = "▶"
                    else:
                        player.paused.set()
                        _action[0] = "⏸"
                elif ch == "\x1b":
                    nxt = sys.stdin.read(1)
                    if nxt == "[":
                        arrow = sys.stdin.read(1)
                        if arrow == "C":  # →
                            player.seek(+player.seek_samples)
                            _action[0] = "+5s"
                        elif arrow == "D":  # ←
                            player.seek(-player.seek_samples)
                            _action[0] = "-5s"
                elif ch in ("\x03", "\x04", "q"):
                    player.stopped.set()
                    break
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    _ = sys.stderr.write("\033[0mPlaying… (space  ←/→=seek 5s  q=quit)\n\033[?25l")
    _ = sys.stderr.flush()

    def _progress_loop() -> None:
        while not done.is_set():
            action = _action[0]
            synth_done = player.synthesis_done.is_set()
            line = _render_bar(
                player.playhead, player.total(), synth_done, SAMPLE_RATE, action=action
            )
            _ = sys.stderr.write(line)
            _ = sys.stderr.flush()
            _ = threading.Event().wait(0.1)
        # Clear progress line and restore cursor
        _ = sys.stderr.write("\r" + " " * 70 + "\r\033[?25h")
        _ = sys.stderr.flush()

    with sd.OutputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=player.callback
    ) as stream:
        key_thread = threading.Thread(target=_keyreader, daemon=True)
        key_thread.start()
        progress_thread = threading.Thread(target=_progress_loop, daemon=True)
        progress_thread.start()

        async def run() -> None:
            async for chunk, _ in synthesise_stream(text, voice=voice, speed=speed):
                if player.stopped.is_set():
                    return
                player.push(chunk)
            player.synthesis_done.set()

        asyncio.run(run())
        # Poll until the callback raises CallbackStop (stream becomes inactive)
        while stream.active:
            _ = threading.Event().wait(0.05)
        done.set()


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
