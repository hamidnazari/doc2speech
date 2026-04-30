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
@click.argument("input_file", default="-", metavar="FILE")
@click.option("-o", "--output", "output_path", default=None, metavar="FILE",
              help="Output WAV file. Defaults to stdout (binary).")
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
    voice: str,
    speed: float,
    no_strip_markdown: bool,
) -> None:
    """Convert a text or markdown FILE to speech.

    Pass '-' or omit FILE to read from stdin.
    """
    from doc2speech.synth import SAMPLE_RATE, synthesise
    from doc2speech.text import load, strip_markdown

    console.print(f"[bold cyan]doc2speech[/] loading {input_file!r}…")
    raw = load(input_file)

    text = raw if no_strip_markdown else strip_markdown(raw)
    if not text.strip():
        console.print("[red]Error:[/] no text to synthesise.")
        raise SystemExit(1)

    console.print(f"[dim]{len(text)} chars → voice=[bold]{voice}[/] speed={speed}[/]")
    console.print("[dim]Synthesising… (first run downloads ~90 MB model)[/]")

    samples = synthesise(text, voice=voice, speed=speed)

    import soundfile as sf

    if output_path:
        sf.write(output_path, samples, SAMPLE_RATE)
        console.print(f"[green]✓[/] Written to [bold]{output_path}[/]")
    else:
        # Binary WAV to stdout for pipeline use
        import io
        buf = io.BytesIO()
        sf.write(buf, samples, SAMPLE_RATE, format="WAV")
        sys.stdout.buffer.write(buf.getvalue())


if __name__ == "__main__":
    cli()
