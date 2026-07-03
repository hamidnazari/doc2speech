from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from markdown_it.token import Token


def load(source: str | None) -> str:
    """Read text from a file path or stdin ('-')."""
    if source is None or source == "-":
        return sys.stdin.read()
    try:
        return Path(source).read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise click.BadParameter(f"File not found: {source}", param_hint="FILE") from e
    except PermissionError as e:
        raise click.BadParameter(f"Permission denied: {source}", param_hint="FILE") from e
    except OSError as e:
        raise click.BadParameter(str(e), param_hint="FILE") from e


def strip_markdown(text: str) -> str:
    """Convert markdown to plain text suitable for TTS."""
    from markdown_it import MarkdownIt

    md = MarkdownIt()
    tokens = md.parse(text)
    plain = _render_tokens(tokens)
    plain = re.sub(r"\n{3,}", "\n\n", plain)
    return plain.strip()


def split_sentences(text: str, max_chars: int = 200) -> list[str]:
    """Split text into segments ≤ max_chars, honouring paragraph breaks first."""
    result: list[str] = []
    for para in re.split(r"\n{2,}", text.strip()):
        para = para.strip()
        if not para:
            continue
        result.extend(_split_para(para, max_chars))
    return result


def _split_para(text: str, max_chars: int) -> list[str]:
    """Split a single paragraph into segments ≤ max_chars on sentence then word boundaries."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
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
        elif tok.type == "heading_close":
            parts.append("\n\n")
        elif tok.type in {
            "hardbreak",
            "paragraph_close",
            "bullet_list_close",
            "hr",
        }:
            parts.append("\n")
    return "".join(parts)
