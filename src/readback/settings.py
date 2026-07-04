from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import click

VOICES = [
    "af_heart",
    "af_bella",
    "af_nicole",
    "af_sarah",
    "af_sky",
    "am_adam",
    "am_michael",
    "bf_emma",
    "bf_isabella",
    "bm_george",
    "bm_lewis",
]

DEFAULT_VOICE = "af_heart"
DEFAULT_SPEED = 1.0
MIN_SPEED = 0.25
MAX_SPEED = 4.0
SPEED_TYPE = click.FloatRange(MIN_SPEED, MAX_SPEED)


@dataclass(frozen=True)
class UserConfig:
    voice: str | None = None
    speed: float | None = None
    play: bool | None = None
    strip_markdown: bool | None = None


def config_path() -> Path:
    return Path.home() / ".config" / "readback" / "config.toml"


def load_user_config(path: Path | None = None) -> UserConfig:
    import tomllib

    path = path or config_path()
    if not path.exists():
        return UserConfig()
    try:
        raw = cast("dict[str, object]", tomllib.loads(path.read_text(encoding="utf-8")))
    except tomllib.TOMLDecodeError as e:
        raise click.ClickException(f"Invalid config file {path}: {e}") from e
    except OSError as e:
        raise click.ClickException(f"Failed to read config file {path}: {e}") from e
    return _parse_config(raw, path)


def _parse_config(raw: dict[str, object], path: Path) -> UserConfig:
    allowed = {"voice", "speed", "play", "strip_markdown"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        keys = ", ".join(unknown)
        raise click.ClickException(f"Invalid config file {path}: unsupported key(s): {keys}")

    voice = _optional_str(raw, "voice", path)
    if voice is not None:
        voice = voice.lower()
        if voice not in VOICES:
            raise click.ClickException(f"Invalid config file {path}: unsupported voice {voice!r}")

    speed = _optional_number(raw, "speed", path)
    if speed is not None and not MIN_SPEED <= speed <= MAX_SPEED:
        raise click.ClickException(
            f"Invalid config file {path}: speed must be between {MIN_SPEED} and {MAX_SPEED}"
        )

    play = _optional_bool(raw, "play", path)
    strip_markdown = _optional_bool(raw, "strip_markdown", path)

    return UserConfig(voice=voice, speed=speed, play=play, strip_markdown=strip_markdown)


def _optional_str(raw: dict[str, object], key: str, path: Path) -> str | None:
    if key not in raw:
        return None
    value = raw[key]
    if not isinstance(value, str):
        raise click.ClickException(f"Invalid config file {path}: {key} must be a string")
    return value


def _optional_number(raw: dict[str, object], key: str, path: Path) -> float | None:
    if key not in raw:
        return None
    value = raw[key]
    if not isinstance(value, int | float):
        raise click.ClickException(f"Invalid config file {path}: {key} must be a number")
    return float(value)


def _optional_bool(raw: dict[str, object], key: str, path: Path) -> bool | None:
    if key not in raw:
        return None
    value = raw[key]
    if not isinstance(value, bool):
        raise click.ClickException(f"Invalid config file {path}: {key} must be true or false")
    return value
