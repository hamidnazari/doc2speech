default:
    @just --list

# Install readback as a global uv tool
[group('run')]
install:
    uv tool install . --force

# Convert a file to a WAV output file
[group('run')]
speak file output voice="af_heart" speed="1.0":
    uv run readback "{{file}}" -o "{{output}}" --voice "{{voice}}" --speed "{{speed}}"

# Stream a file to ffplay (starts playing before synthesis completes)
[group('run')]
play file voice="af_heart" speed="1.0":
    uv run readback "{{file}}" --play --voice "{{voice}}" --speed "{{speed}}"

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
