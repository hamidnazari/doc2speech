# doc2speech

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
just install

# Or run directly without installing
uv run doc2speech --help
```

Requires Python ≥ 3.12 and [uv](https://docs.astral.sh/uv/).

## Usage

```
doc2speech [OPTIONS] [FILE]
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
doc2speech README.md --play

# Save to WAV
doc2speech notes.md -o notes.wav

# Read from stdin, pipe to ffplay
echo "Hello, world." | doc2speech | ffplay -i -

# Change voice and speed
doc2speech article.md --play --voice bm_george --speed 1.2
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
