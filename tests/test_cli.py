from __future__ import annotations

import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from doc2speech.__main__ import cli


def test_missing_file_gives_clean_error() -> None:
    result = CliRunner().invoke(cli, ["/nonexistent/file.md"])
    assert result.exit_code != 0
    assert "File not found" in result.output


def test_empty_file_gives_clean_error(tmp_path: Path) -> None:
    f = tmp_path / "empty.txt"
    _ = f.write_text("", encoding="utf-8")
    result = CliRunner().invoke(cli, [str(f)])
    assert result.exit_code == 1
    assert "no text" in result.output


def test_missing_dependency_gives_clean_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    f = tmp_path / "hello.txt"
    _ = f.write_text("Hello world.", encoding="utf-8")

    # Simulate sounddevice not being installed
    monkeypatch.setitem(sys.modules, "sounddevice", None)

    result = CliRunner().invoke(cli, ["--play", str(f)])
    assert result.exit_code == 1
    assert "Missing dependency" in result.output
