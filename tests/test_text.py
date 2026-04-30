from __future__ import annotations

from doc2speech.text import strip_markdown


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
