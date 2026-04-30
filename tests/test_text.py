from __future__ import annotations

from pathlib import Path

import pytest

from doc2speech.text import load, strip_markdown


def test_strips_headings() -> None:
    result = strip_markdown("# Hello\n\nWorld")
    assert "Hello" in result
    assert "#" not in result


def test_strips_bold() -> None:
    result = strip_markdown("This is **bold** text.")
    assert "bold" in result
    assert "*" not in result


def test_preserves_plain_text() -> None:
    plain = "Just a sentence."
    assert strip_markdown(plain) == plain


def test_strips_italic() -> None:
    result = strip_markdown("This is _italic_ text.")
    assert "italic" in result
    assert "_" not in result


def test_strips_links() -> None:
    result = strip_markdown("Visit [example](https://example.com) for more.")
    assert "example" in result
    assert "https://" not in result
    assert "[" not in result


def test_strips_code_inline() -> None:
    result = strip_markdown("Run `ls -la` to list files.")
    assert "ls -la" in result
    assert "`" not in result


def test_strips_fenced_code_block() -> None:
    result = strip_markdown("```python\nprint('hello')\n```")
    assert "print('hello')" in result
    assert "```" not in result


def test_collapses_excess_blank_lines() -> None:
    result = strip_markdown("One\n\n\n\n\nTwo")
    assert "\n\n\n" not in result


def test_empty_string_returns_empty() -> None:
    assert strip_markdown("") == ""


def test_strips_horizontal_rule() -> None:
    result = strip_markdown("Above\n\n---\n\nBelow")
    assert "Above" in result
    assert "Below" in result
    assert "---" not in result


def test_load_from_file(tmp_path: Path) -> None:
    f = tmp_path / "sample.txt"
    _ = f.write_text("Hello from file", encoding="utf-8")
    assert load(str(f)) == "Hello from file"


def test_load_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("stdin content"))
    assert load("-") == "stdin content"


def test_load_none_reads_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("from none"))
    assert load(None) == "from none"
