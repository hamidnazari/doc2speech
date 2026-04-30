default:
    @just --list

# Install doc2speech as a global uv tool
[group('run')]
install:
    uv tool install .

# Convert a file to speech (writes WAV to stdout)
[group('run')]
speak file voice="af_heart" speed="1.0":
    uv run doc2speech "{{file}}" --voice "{{voice}}" --speed "{{speed}}"

# Convert a file to a WAV output file
[group('run')]
speak-file file output voice="af_heart" speed="1.0":
    uv run doc2speech "{{file}}" -o "{{output}}" --voice "{{voice}}" --speed "{{speed}}"

# Play a file via afplay (macOS)
[group('run')]
play file voice="af_heart" speed="1.0":
    #!/usr/bin/env bash
    set -euo pipefail
    tmp=$(mktemp /tmp/doc2speech.XXXXXX.wav)
    trap "rm -f \"$tmp\"" EXIT
    uv run doc2speech "{{file}}" --voice "{{voice}}" --speed "{{speed}}" -o "$tmp"
    afplay "$tmp"

# Run the test suite
[group('dev')]
test *args:
    uv run pytest {{args}}

# Lint with ruff
[group('dev')]
lint:
    uv run ruff check .

# Type-check with basedpyright
[group('dev')]
typecheck:
    uv run basedpyright

# Format with ruff
[group('dev')]
fmt:
    uv run ruff format .

# Run all quality checks
[group('dev')]
qa: test lint typecheck
