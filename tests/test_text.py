from __future__ import annotations

from pathlib import Path

import pytest

from doc2speech.text import load, split_sentences, strip_markdown


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


# ---------------------------------------------------------------------------
# split_sentences
# ---------------------------------------------------------------------------


def test_split_short_text_is_single_segment() -> None:
    result = split_sentences("Hello world.")
    assert result == ["Hello world."]


def test_split_respects_max_chars() -> None:
    long = ("The fox jumps. " * 30).strip()
    segments = split_sentences(long, max_chars=100)
    assert all(len(s) <= 100 for s in segments)
    assert len(segments) > 1


def test_split_preserves_all_content() -> None:
    text = "First sentence. Second sentence! Third sentence?"
    segments = split_sentences(text, max_chars=30)
    joined = " ".join(segments)
    assert "First sentence." in joined
    assert "Second sentence!" in joined
    assert "Third sentence?" in joined


def test_split_empty_string_returns_empty() -> None:
    assert split_sentences("") == []


def test_split_single_long_sentence_splits_on_word_boundary() -> None:
    # A single sentence exceeding max_chars must be split on word boundaries
    long = " ".join(["word"] * 100)  # ~499 chars, no sentence punctuation
    result = split_sentences(long, max_chars=100)
    assert all(len(s) <= 100 for s in result)
    assert len(result) > 1


def test_split_single_long_word_hard_cuts() -> None:
    # A single token longer than max_chars falls back to a hard character cut
    long = "a" * 200
    result = split_sentences(long, max_chars=100)
    assert all(len(s) <= 100 for s in result)
    assert "".join(result) == long


def test_split_default_max_chars_is_300() -> None:
    # Default must stay at 300 to stay well under kokoro's 510-phoneme limit
    text = ("Hello world. " * 25).strip()  # ~325 chars
    result = split_sentences(text)
    assert all(len(s) <= 300 for s in result)


def test_split_aggregates_short_sentences() -> None:
    text = "A. B. C. D."
    result = split_sentences(text, max_chars=50)
    # All four short sentences should be merged into one segment
    assert len(result) == 1
    assert result[0] == "A. B. C. D."


def test_split_heading_separated_from_paragraph() -> None:
    # Heading and following paragraph must be in separate segments
    text = "Introduction\n\nThis is the first paragraph."
    result = split_sentences(text, max_chars=300)
    assert result[0] == "Introduction"
    assert result[1] == "This is the first paragraph."


def test_strip_markdown_heading_becomes_separate_paragraph() -> None:
    # strip_markdown must emit a blank line after headings so split_sentences
    # sees them as separate paragraphs
    result = strip_markdown("# My Heading\n\nSome content here.")
    assert "My Heading\n\nSome content" in result
