from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdown_it.token import Token


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
    plain = re.sub(r"\n{3,}", "\n\n", plain)
    return plain.strip()


def split_sentences(text: str, max_chars: int = 300) -> list[str]:
    """Split text into segments ≤ max_chars, breaking on sentence then word boundaries."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    segments: list[str] = []
    buf = ""
    for sent in sentences:
        if not sent:
            continue
        if buf and len(buf) + 1 + len(sent) > max_chars:
            segments.append(buf)
            buf = sent
        else:
            buf = f"{buf} {sent}".strip() if buf else sent
        while len(buf) > max_chars:
            cut = buf.rfind(" ", 0, max_chars)
            if cut == -1:
                cut = max_chars
            segments.append(buf[:cut])
            buf = buf[cut:].lstrip()
    if buf:
        segments.append(buf)
    return segments


def _render_tokens(tokens: list[Token]) -> str:
    parts: list[str] = []
    for tok in tokens:
        if tok.type == "inline" and tok.children:
            parts.append(_render_tokens(tok.children))
        elif tok.type in ("text", "code_inline", "fence", "code_block"):
            parts.append(tok.content)
        elif tok.type == "softbreak":
            parts.append(" ")
        elif tok.type in {
            "hardbreak",
            "paragraph_close",
            "heading_close",
            "bullet_list_close",
            "hr",
        }:
            parts.append("\n")
    return "".join(parts)
