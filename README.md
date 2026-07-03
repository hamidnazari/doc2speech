# readback

Convert text or Markdown documents to speech using [Kokoro ONNX](https://github.com/thewh1teagle/kokoro-onnx) — a lightweight, offline TTS engine.

## Features

- Reads plain text or Markdown files (strips formatting automatically)
- Streams audio to your speakers as synthesis proceeds, or saves to WAV
- Interactive playback controls: pause/resume, seek ±5 s, quit
- Pipes cleanly — write WAV bytes to stdout for use with `ffplay`, `sox`, etc.
- 11 built-in voices (American and British English)
- Model files downloaded automatically on first use (~`~/.cache/kokoro/`)

## Installation

```sh
# Install as a global uv tool
uv tool install .

# Or run directly without installing
uv run readback --help
```

Requires Python ≥ 3.12. If you do not use [uv](https://docs.astral.sh/uv/), install with pipx or pip:

```sh
pipx install .
python -m pip install .
python -m readback --help
```

## Usage

```
readback [OPTIONS] [FILE]
```

`FILE` defaults to `-` (stdin).

| Option | Default | Description |
|---|---|---|
| `-o FILE` / `--output FILE` | — | Save audio to a WAV file |
| `--play` | off | Stream to default audio device |
| `--voice VOICE` | `af_heart` | Kokoro voice ID (see below) |
| `--speed FLOAT` | `1.0` | Speech speed multiplier |
| `--no-strip-markdown` | off | Pass raw text without stripping Markdown |

### Playback controls (interactive mode)

| Key | Action |
|---|---|
| `Space` | Pause / resume |
| `→` | Seek forward 5 s |
| `←` | Seek backward 5 s |
| `q` / `Ctrl-C` | Quit |

### Examples

```sh
# Play a Markdown file aloud
readback README.md --play

# Save to WAV
readback notes.md -o notes.wav

# Read from stdin, pipe to ffplay
echo "Hello, world." | readback | ffplay -i -

# Change voice and speed
readback article.md --play --voice bm_george --speed 1.2
```

## Voices

| ID | Accent |
|---|---|
| `af_heart` *(default)* | American Female |
| `af_bella` | American Female |
| `af_nicole` | American Female |
| `af_sarah` | American Female |
| `af_sky` | American Female |
| `am_adam` | American Male |
| `am_michael` | American Male |
| `bf_emma` | British Female |
| `bf_isabella` | British Female |
| `bm_george` | British Male |
| `bm_lewis` | British Male |

## Development

```sh
just qa        # tests + lint + type-check
just test      # pytest only
just lint      # ruff check
just typecheck # basedpyright
just fmt       # ruff format
```
