from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List

BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "div",
    "dl",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "section",
    "table",
    "tr",
    "td",
    "th",
    "ul",
}

PLACEHOLDER_PATTERNS = [
    re.compile(r"\{\([A-Z0-9_]+\)\}"),
    re.compile(r"@/[^/]+/@"),
]

URL_PATTERN = re.compile(r"(https?://\S+|www\.\S+)", flags=re.IGNORECASE)


@dataclass
class ExportRules:
    profile: str
    separator_char: str = "*"
    separator_length: int = 124
    link_style: str = "stacked"
    max_blank_lines: int = 0
    include_separator_on_hr: bool = True
    emit_alt_as_content: bool = True
    dedupe_consecutive_lines: bool = True
    trim_before_publicidad: bool = True
    max_repeated_url_lines: int = 2
    max_repeated_short_lines: int = 2


PROFILE_RULES: Dict[str, ExportRules] = {
    "merchant": ExportRules(profile="merchant", separator_char="*", separator_length=124, link_style="stacked", emit_alt_as_content=True),
    "pp": ExportRules(profile="pp", separator_char="*", separator_length=124, link_style="stacked", emit_alt_as_content=True),
    "mr_plat": ExportRules(profile="mr_plat", separator_char="*", separator_length=98, link_style="stacked", emit_alt_as_content=True),
    "mr_cent": ExportRules(profile="mr_cent", separator_char="*", separator_length=99, link_style="inline", emit_alt_as_content=True),
}


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def detect_profile(html_text: str) -> str:
    t = html_text.lower()
    if "centurion" in t:
        return "mr_cent"
    if "membership rewards" in t and "smiles" in t:
        return "mr_plat"
    if "ultramarino" in t or "platinum concierge" in t:
        return "pp"
    return "merchant"


def get_rules(profile: str) -> ExportRules:
    return PROFILE_RULES.get(profile, PROFILE_RULES["merchant"])


def extract_placeholders(text: str) -> List[str]:
    found: List[str] = []
    for pattern in PLACEHOLDER_PATTERNS:
        for match in pattern.finditer(text):
            found.append(match.group(0))
    return sorted(set(found))


def fix_url(url: str) -> str:
    normalized = (url or "").strip()
    if not normalized:
        return ""
    normalized = re.sub(r"^hhttps://", "https://", normalized, flags=re.IGNORECASE)
    match = re.match(r"^(https?://\S+)\((https?://\S+)\)$", normalized, flags=re.IGNORECASE)
    if match:
        return match.group(2)
    return normalized


def normalize_line_clean(line: str) -> str:
    out = re.sub(r"hhttps://", "https://", line, flags=re.IGNORECASE)
    out = re.sub(r"(https?://\S+)\((https?://\S+)\)", r"\2", out, flags=re.IGNORECASE)
    return out


def is_meaningful_alt(alt: str) -> bool:
    if not alt:
        return False
    normalized = normalize_spaces(alt)
    if not normalized:
        return False
    if normalized in {"*", "+", "-", "|"}:
        return False
    if re.fullmatch(r"[-*+\sÃ³]+", normalized, flags=re.IGNORECASE):
        return False
    return len(normalized) >= 2
