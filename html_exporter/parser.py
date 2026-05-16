from __future__ import annotations

import html
import re
import urllib.parse
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional, Tuple

from .rules import (
    BLOCK_TAGS,
    ExportRules,
    fix_url,
    is_meaningful_alt,
    normalize_line_clean,
    normalize_spaces,
)


@dataclass
class ImageAsset:
    src: str
    alt: str
    filename: str


_BORDER_RE_CACHE: dict = {}


def _has_solid_border(style: str, prop: str) -> bool:
    """True si el style CSS declara `prop` (border-top|border-bottom) con `solid` y al menos 1px."""
    if not style or prop not in style:
        return False
    pattern = _BORDER_RE_CACHE.get(prop)
    if pattern is None:
        pattern = re.compile(
            rf"{re.escape(prop)}\s*:\s*(?:solid\s+\d+px|\d+px\s+solid)",
            re.IGNORECASE,
        )
        _BORDER_RE_CACHE[prop] = pattern
    return bool(pattern.search(style))


def extract_filename_from_src(src: str) -> str:
    if not src:
        return ""
    cleaned = src.strip()
    if re.match(r"^https?://", cleaned, flags=re.IGNORECASE):
        try:
            parsed = urllib.parse.urlparse(cleaned)
            return Path(parsed.path).name
        except Exception:
            return Path(cleaned).name
    cleaned = re.split(r"[?#]", cleaned)[0]
    return Path(cleaned.replace("\\", "/")).name


class EmailHTMLToTextParser(HTMLParser):
    def __init__(self, mode: str, rules: ExportRules):
        super().__init__(convert_charrefs=True)
        self.mode = mode
        self.rules = rules
        self.lines: List[str] = []
        self.current_line: List[str] = []
        self.images: List[ImageAsset] = []
        self.ignore_depth = 0
        self.anchor_href: Optional[str] = None
        self.anchor_text_parts: List[str] = []
        self.anchor_img_alt_parts: List[str] = []
        self.last_emitted_was_blank = True
        self.warnings: List[str] = []
        self.border_bottom_stack: List[tuple] = []

    def separator_line(self) -> str:
        return self.rules.separator_char * self.rules.separator_length

    def emit_separator(self) -> None:
        self.flush_line()
        self.emit_line(self.separator_line())
        self.emit_blank()

    def emit_blank(self) -> None:
        if not self.last_emitted_was_blank:
            self.lines.append("")
            self.last_emitted_was_blank = True

    def emit_line(self, text: str) -> None:
        normalized = normalize_spaces(text)
        if not normalized:
            return
        if self.mode == "clean":
            normalized = normalize_line_clean(normalized)
        self.lines.append(normalized)
        self.last_emitted_was_blank = False

    def flush_line(self) -> None:
        if not self.current_line:
            return
        text = normalize_spaces(" ".join(self.current_line))
        self.current_line = []
        if text:
            self.emit_line(text)

    def emit_text_fragment(self, text: str) -> None:
        normalized = normalize_spaces(text)
        if not normalized:
            return
        self.current_line.append(normalized)
        self.last_emitted_was_blank = False

    def emit_link(self, text: str, href: str) -> None:
        url = fix_url(href) if self.mode == "clean" else href.strip()
        label = normalize_spaces(text)
        if not url:
            if label:
                self.emit_line(label)
            return

        if self.rules.link_style == "inline":
            self.emit_line(f"{label}({url})" if label else url)
            return

        if label:
            self.emit_line(label)
        self.emit_line(url)

    def handle_starttag(self, tag: str, attrs) -> None:
        lower_tag = tag.lower()
        attrs_dict = dict(attrs)

        if lower_tag in {"script", "style"}:
            self.ignore_depth += 1
            return
        if self.ignore_depth > 0:
            return

        if lower_tag == "br":
            self.flush_line()
            return

        if lower_tag == "hr":
            if self.rules.include_separator_on_hr:
                self.emit_separator()
            return

        if lower_tag in {"td", "tr"} and self.rules.include_separator_on_hr:
            style = (attrs_dict.get("style") or "").lower()
            if _has_solid_border(style, "border-top"):
                self.emit_separator()
            has_bottom = _has_solid_border(style, "border-bottom")
            self.border_bottom_stack.append((lower_tag, has_bottom))

        if lower_tag in BLOCK_TAGS:
            self.flush_line()

        if lower_tag == "a":
            self.anchor_href = attrs_dict.get("href", "").strip()
            self.anchor_text_parts = []
            self.anchor_img_alt_parts = []
            return

        if lower_tag == "img":
            src = attrs_dict.get("src", "").strip()
            alt = html.unescape(attrs_dict.get("alt", "")).strip()
            filename = extract_filename_from_src(src)
            if filename:
                self.images.append(ImageAsset(src=src, alt=alt, filename=filename))

            if self.anchor_href is not None:
                if is_meaningful_alt(alt):
                    self.anchor_img_alt_parts.append(normalize_spaces(alt))
            elif self.rules.emit_alt_as_content and is_meaningful_alt(alt):
                self.flush_line()
                self.emit_line(alt)

    def handle_endtag(self, tag: str) -> None:
        lower_tag = tag.lower()

        if lower_tag in {"script", "style"} and self.ignore_depth > 0:
            self.ignore_depth -= 1
            return
        if self.ignore_depth > 0:
            return

        if lower_tag in {"td", "tr"} and self.rules.include_separator_on_hr:
            for i in range(len(self.border_bottom_stack) - 1, -1, -1):
                if self.border_bottom_stack[i][0] == lower_tag:
                    _, had_bottom = self.border_bottom_stack.pop(i)
                    if had_bottom:
                        self.emit_separator()
                    break

        if lower_tag == "a" and self.anchor_href is not None:
            link_text = normalize_spaces(" ".join(self.anchor_text_parts))
            if not link_text and self.anchor_img_alt_parts:
                link_text = normalize_spaces(" ".join(self.anchor_img_alt_parts))
            self.flush_line()
            self.emit_link(link_text, self.anchor_href)
            self.anchor_href = None
            self.anchor_text_parts = []
            self.anchor_img_alt_parts = []
            self.emit_blank()
            return

        if lower_tag in BLOCK_TAGS:
            self.flush_line()

    def handle_data(self, data: str) -> None:
        if self.ignore_depth > 0:
            return
        text = html.unescape(data or "")
        if not text.strip():
            return
        if self.anchor_href is not None:
            self.anchor_text_parts.append(text)
        else:
            self.emit_text_fragment(text)

    def finalize(self) -> Tuple[List[str], List[ImageAsset], List[str]]:
        self.flush_line()
        cleaned: List[str] = []
        blank_count = 0
        max_blank = max(0, self.rules.max_blank_lines)

        for line in self.lines:
            stripped = line.rstrip()
            if not stripped:
                blank_count += 1
                if blank_count <= max_blank:
                    cleaned.append("")
                continue
            blank_count = 0
            cleaned.append(stripped)

        while cleaned and cleaned[-1] == "":
            cleaned.pop()

        return cleaned, self.images, self.warnings
