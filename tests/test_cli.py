from __future__ import annotations

import sys
from pathlib import Path

import pytest
from click.testing import CliRunner
from rich.console import Console

from readback.__main__ import cli


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


def test_speed_rejects_zero() -> None:
    result = CliRunner().invoke(cli, ["--speed", "0", "-"])
    assert result.exit_code != 0
    assert "Invalid value for '--speed'" in result.output


def test_speed_accepts_valid_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    f = tmp_path / "hello.txt"
    _ = f.write_text("Hello world.", encoding="utf-8")
    calls: list[tuple[str, float]] = []

    def fake_write_file(
        _text: str, voice: str, speed: float, _output_path: str, _console: Console
    ) -> None:
        calls.append((voice, speed))

    monkeypatch.setattr("readback.output.write_file", fake_write_file)
    result = CliRunner().invoke(cli, ["--speed", "1.25", "-o", "out.wav", str(f)])
    assert result.exit_code == 0
    assert calls == [("af_heart", 1.25)]


def test_config_defaults_are_used(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    config_dir = home / ".config" / "readback"
    config_dir.mkdir(parents=True)
    _ = (config_dir / "config.toml").write_text(
        'voice = "bm_george"\nspeed = 1.5\nstrip_markdown = false\n',
        encoding="utf-8",
    )
    f = tmp_path / "hello.md"
    _ = f.write_text("Hello **world**.", encoding="utf-8")
    calls: list[tuple[str, str, float]] = []

    def fake_write_file(
        text: str, voice: str, speed: float, _output_path: str, _console: Console
    ) -> None:
        calls.append((text, voice, speed))

    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    monkeypatch.setattr("readback.output.write_file", fake_write_file)
    result = CliRunner().invoke(cli, ["-o", "out.wav", str(f)])
    assert result.exit_code == 0
    assert calls == [("Hello **world**.", "bm_george", 1.5)]


def test_cli_flags_override_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    config_dir = home / ".config" / "readback"
    config_dir.mkdir(parents=True)
    _ = (config_dir / "config.toml").write_text(
        'voice = "bm_george"\nspeed = 1.5\n',
        encoding="utf-8",
    )
    f = tmp_path / "hello.txt"
    _ = f.write_text("Hello world.", encoding="utf-8")
    calls: list[tuple[str, float]] = []

    def fake_write_file(
        _text: str, voice: str, speed: float, _output_path: str, _console: Console
    ) -> None:
        calls.append((voice, speed))

    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    monkeypatch.setattr("readback.output.write_file", fake_write_file)
    result = CliRunner().invoke(
        cli, ["--voice", "af_bella", "--speed", "0.75", "-o", "out.wav", str(f)]
    )
    assert result.exit_code == 0
    assert calls == [("af_bella", 0.75)]


def test_invalid_config_fails_before_synthesis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    config_dir = home / ".config" / "readback"
    config_dir.mkdir(parents=True)
    _ = (config_dir / "config.toml").write_text("speed = 99\n", encoding="utf-8")
    f = tmp_path / "hello.txt"
    _ = f.write_text("Hello world.", encoding="utf-8")

    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    result = CliRunner().invoke(cli, ["-o", "out.wav", str(f)])
    assert result.exit_code != 0
    assert "Invalid config file" in result.output
