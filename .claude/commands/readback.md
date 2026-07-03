---
description: Work on the readback text-to-speech CLI
argument-hint: [TASK]
---

You are working in the readback repository, a Python CLI that converts text or Markdown documents to speech with Kokoro ONNX.

Task: $ARGUMENTS

Use the existing project conventions:

- Runtime package: `src/readback`
- CLI command: `readback`
- Tests: `tests`
- Quality gate: `just qa`

When changing behavior, add or update focused tests. Prefer `just test`, `just lint`, and `just typecheck` while iterating, then run `just qa` before finishing. Keep README, `pyproject.toml`, and `Justfile` aligned with any CLI or packaging changes.
