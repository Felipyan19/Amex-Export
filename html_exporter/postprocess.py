from __future__ import annotations

import re
from typing import Dict, List

from .rules import ExportRules, PLACEHOLDER_PATTERNS, URL_PATTERN, extract_placeholders, normalize_line_clean


def collect_text_stats(lines: List[str]) -> dict:
    url_lines = 0
    inline_url_lines = 0
    separators = 0
    placeholders = set()

    for line in lines:
        if not line:
            continue
        if re.fullmatch(r"\*{20,}|-{6,}.*", line):
            separators += 1
        if URL_PATTERN.search(line):
            url_lines += 1
            if not re.fullmatch(r"(https?://\S+|www\.\S+)", line):
                inline_url_lines += 1
        for placeholder in extract_placeholders(line):
            placeholders.add(placeholder)

    return {
        "total_lines": len(lines),
        "url_lines": url_lines,
        "inline_url_lines": inline_url_lines,
        "separator_lines": separators,
        "placeholders": sorted(placeholders),
    }


def trim_before_publicidad(lines: List[str]) -> List[str]:
    idx = -1
    for i, line in enumerate(lines[:60]):
        if line.strip().upper() == "PUBLICIDAD":
            idx = i
            break
    return lines if idx <= 0 else lines[idx:]


def dedupe_consecutive_lines(lines: List[str]) -> List[str]:
    out: List[str] = []
    prev_key = None
    for line in lines:
        key = line.strip().lower()
        if key and prev_key == key:
            continue
        out.append(line)
        prev_key = key if key else prev_key
    return out


def _line_has_placeholder(line: str) -> bool:
    return any(pattern.search(line) for pattern in PLACEHOLDER_PATTERNS)


def _is_separator_line(line: str) -> bool:
    return bool(re.fullmatch(r"\*{20,}|-{6,}.*", line.strip()))


def reduce_repeated_lines(lines: List[str], rules: ExportRules) -> List[str]:
    out: List[str] = []
    url_count: Dict[str, int] = {}
    short_count: Dict[str, int] = {}

    for line in lines:
        raw = line.strip()
        key = raw.lower()
        if not raw:
            out.append(line)
            continue
        if _is_separator_line(raw) or _line_has_placeholder(raw):
            out.append(line)
            continue

        if re.fullmatch(r"(https?://\S+|www\.\S+|tel:\S+|mailto:\S+)", raw, flags=re.IGNORECASE):
            c = url_count.get(key, 0)
            if c >= rules.max_repeated_url_lines:
                continue
            url_count[key] = c + 1
            out.append(line)
            continue

        if len(raw) <= 70:
            c = short_count.get(key, 0)
            if c >= rules.max_repeated_short_lines:
                continue
            short_count[key] = c + 1
        out.append(line)

    return out


# Mapping bidireccional de placeholders entre sistemas ESP
# Centurion usa @/var/@  —  No-Centurion usa {(VAR)}
_TO_CENTURION: dict = {
    "{(FULLNAME)}": "@/nombre/@",
    "{(EMAIL)}": "@/mailtarget/@",
    "{(LAST_5)}": "@/last5/@",
    "{(MEMBER_SINCE)}": "@/membersince/@",
    "{(URLSignature1)}": "@/viewonline_link/@",
}
_TO_NON_CENTURION: dict = {v: k for k, v in _TO_CENTURION.items()}
# variante mayúscula que aparece en algunas campañas CENT
_TO_NON_CENTURION["@/MAILTARGET/@"] = "{(EMAIL)}"


def normalize_placeholders(lines: List[str], profile: str) -> List[str]:
    if profile == "mr_cent":
        mapping = _TO_CENTURION
    else:
        mapping = _TO_NON_CENTURION
    out = []
    for line in lines:
        value = line
        for src, dst in mapping.items():
            value = value.replace(src, dst)
        out.append(value)
    return out


ENTITY_FIXES = {
    # Mojibake variants
    "Â®": "(R)",
    "Ã‚Â®": "(R)",
    "â„¢": "(TM)",
    "Ã¢â€žÂ¢": "(TM)",
    "Â©": "(C)",
    "Ã‚Â©": "(C)",
    # Unicode reales
    "®": "(R)",   # ®
    "™": "(TM)",  # ™
    "©": "(C)",   # ©
    # Superíndices numéricos (legales)
    "¹": "(1)",   # ¹
    "²": "(2)",   # ²
    "³": "(3)",   # ³
    "⁰": "(0)",   # ⁰
    "⁴": "(4)",   # ⁴
    "⁵": "(5)",   # ⁵
    "⁶": "(6)",   # ⁶
    "⁷": "(7)",   # ⁷
    "⁸": "(8)",   # ⁸
    "⁹": "(9)",   # ⁹
}


def apply_generic_normalizations(lines: List[str]) -> List[str]:
    out: List[str] = []
    for line in lines:
        value = line
        for src, dst in ENTITY_FIXES.items():
            value = value.replace(src, dst)
        value = re.sub(r"\s+\.", ".", value)
        value = re.sub(r"\s+,", ",", value)
        out.append(value)
    return out


def postprocess_lines(lines: List[str], rules: ExportRules, mode: str) -> List[str]:
    out = list(lines)
    if rules.trim_before_publicidad:
        out = trim_before_publicidad(out)
    if rules.dedupe_consecutive_lines:
        out = dedupe_consecutive_lines(out)

    out = reduce_repeated_lines(out, rules)
    out = apply_generic_normalizations(out)
    out = normalize_placeholders(out, rules.profile)

    if mode == "clean":
        out = [normalize_line_clean(x) if x else x for x in out]

    while out and out[-1] == "":
        out.pop()
    return out
