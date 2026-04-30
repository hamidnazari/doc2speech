from __future__ import annotations

import re
import sys
from pathlib import Path


def load(source: str | None) -> str:
    """Read text from a file path or stdin ('-')."""
    if source is None or source == "-":
        return sys.stdin.read()
    return Path(source).read_text(encoding="utf-8")


def strip_markdown(text: str) -> str:
    """Convert markdown to plain text suitable for TTS."""
    from markdown_it import MarkdownIt

    md = MarkdownIt()
    tokens = md.parse(text)
    plain = _render_tokens(tokens)
    # Collapse excessive blank lines
    plain = re.sub(r"\n{3,}", "\n\n", plain)
    return plain.strip()


def _render_tokens(tokens: list) -> str:  # type: ignore[type-arg]
    parts: list[str] = []
    for tok in tokens:
        if tok.type == "inline" and tok.children:
            parts.append(_render_tokens(tok.children))
        elif tok.type in ("text", "code_inline", "fence", "code_block"):
            parts.append(tok.content)
        elif tok.type == "softbreak":
            parts.append(" ")
        elif tok.type in {
            "hardbreak", "paragraph_close", "heading_close", "bullet_list_close", "hr"
        }:
            parts.append("\n")
    return "".join(parts)
