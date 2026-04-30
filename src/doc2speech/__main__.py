from __future__ import annotations

import sys

import click
from rich.console import Console

console = Console(stderr=True)

_VOICES = [
    "af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky",
    "am_adam", "am_michael",
    "bf_emma", "bf_isabella",
    "bm_george", "bm_lewis",
]


@click.command()
@click.version_option(package_name="doc2speech")
@click.argument("input_file", default="-", metavar="FILE")
@click.option("-o", "--output", "output_path", default=None, metavar="FILE",
              help="Output WAV file.")
@click.option("--play", "play", is_flag=True, default=False,
              help="Stream audio to ffplay as chunks are synthesised.")
@click.option("--voice", default="af_heart", show_default=True,
              type=click.Choice(_VOICES, case_sensitive=False),
              help="Kokoro voice ID.")
@click.option("--speed", default=1.0, show_default=True, type=float,
              help="Speech speed multiplier.")
@click.option("--no-strip-markdown", is_flag=True, default=False,
              help="Disable markdown stripping (pass raw text).")
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


def _play_stream(text: str, voice: str, speed: float) -> None:
    import asyncio
    import subprocess

    from doc2speech.synth import SAMPLE_RATE, synthesise_stream

    proc = subprocess.Popen(
        ["ffplay", "-f", "f32le", "-ar", str(SAMPLE_RATE), "-ch_layout", "mono",
         "-nodisp", "-autoexit", "-i", "pipe:0"],
        stdin=subprocess.PIPE,
    )
    assert proc.stdin is not None

    console.print("[dim]Streaming to ffplay…[/]")

    async def run() -> None:
        async for chunk, _ in synthesise_stream(text, voice=voice, speed=speed):
            proc.stdin.write(chunk.astype("float32").tobytes())  # type: ignore[union-attr]
        proc.stdin.close()  # type: ignore[union-attr]

    asyncio.run(run())
    proc.wait()


def _write_file(text: str, voice: str, speed: float, output_path: str) -> None:
    import soundfile as sf

    from doc2speech.synth import SAMPLE_RATE, synthesise

    console.print("[dim]Synthesising…[/]")
    samples = synthesise(text, voice=voice, speed=speed)
    sf.write(output_path, samples, SAMPLE_RATE)
    console.print(f"[green]✓[/] Written to [bold]{output_path}[/]")


def _write_stdout(text: str, voice: str, speed: float) -> None:
    import io

    import soundfile as sf

    from doc2speech.synth import SAMPLE_RATE, synthesise

    console.print("[dim]Synthesising…[/]")
    samples = synthesise(text, voice=voice, speed=speed)
    buf = io.BytesIO()
    sf.write(buf, samples, SAMPLE_RATE, format="WAV")
    sys.stdout.buffer.write(buf.getvalue())


if __name__ == "__main__":
    cli()
