from __future__ import annotations

import sys

import click
from click.core import ParameterSource
from rich.console import Console

from readback.settings import DEFAULT_SPEED, DEFAULT_VOICE, SPEED_TYPE, VOICES, load_user_config

console = Console(stderr=True)


@click.command()
@click.version_option(package_name="readback")
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
    default=DEFAULT_VOICE,
    show_default=True,
    type=click.Choice(VOICES, case_sensitive=False),
    help="Kokoro voice ID.",
)
@click.option(
    "--speed",
    default=DEFAULT_SPEED,
    show_default=True,
    type=SPEED_TYPE,
    help="Speech speed multiplier.",
)
@click.option(
    "--no-strip-markdown",
    is_flag=True,
    default=False,
    help="Disable markdown stripping (pass raw text).",
)
@click.pass_context
def cli(
    ctx: click.Context,
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
    from readback.text import load, strip_markdown

    config = load_user_config()
    if ctx.get_parameter_source("voice") is ParameterSource.DEFAULT and config.voice is not None:
        voice = config.voice
    if ctx.get_parameter_source("speed") is ParameterSource.DEFAULT and config.speed is not None:
        speed = config.speed
    if ctx.get_parameter_source("play") is ParameterSource.DEFAULT and config.play is not None:
        play = config.play
    if (
        ctx.get_parameter_source("no_strip_markdown") is ParameterSource.DEFAULT
        and config.strip_markdown is not None
    ):
        no_strip_markdown = not config.strip_markdown

    console.print(f"[bold cyan]readback[/] loading {input_file!r}…")
    raw = load(input_file)

    text = raw if no_strip_markdown else strip_markdown(raw)
    if not text.strip():
        console.print("[red]Error:[/] no text to synthesise.")
        raise SystemExit(1)

    try:
        if output_path:
            from readback.output import write_file

            write_file(text, voice, speed, output_path, console)
        elif play or sys.stdout.isatty():
            from readback.playback import play_stream

            console.print(
                f"[dim]{len(text)} chars → voice=[bold]{voice}[/bold] speed={speed}[/dim]"
            )
            _ = console.file.write("\033[0m")
            console.file.flush()
            play_stream(text, voice, speed)
        else:
            from readback.output import write_stdout

            write_stdout(text, voice, speed, console)
    except click.ClickException:
        raise
    except ImportError as e:
        console.print(f"[red]Missing dependency:[/] {e}")
        console.print("[dim]Install with: uv tool install .  # or: python -m pip install .[/dim]")
        raise SystemExit(1) from e
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1) from e


if __name__ == "__main__":
    cli()
