"""Verifica que el servicio genera TXT con las reglas estructurales correctas
para cada uno de los samples bajo samples/<profile>/<campaign>/."""
import re
import sys
import tempfile
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
sys.path.insert(0, str(_REPO_ROOT))

from html_export_service import export_html

SAMPLES_DIR = _REPO_ROOT / "samples"

EXPECTED_SEP = {
    "merchant": 124,
    "pp": 124,
    "mr_plat": 98,
    "mr_cent": 99,
}


def iter_sample_pairs():
    for html in sorted(SAMPLES_DIR.rglob("*.html")):
        txt = html.with_suffix(".txt")
        if txt.exists():
            yield html, txt


for html_path, txt_path in iter_sample_pairs():
    with tempfile.TemporaryDirectory() as td:
        result = export_html(
            html_file=html_path,
            out_dir=Path(td) / "out",
            mode="clean",
            profile="auto",
            image_layout="images",
            dry_run_images=True,
        )
        generated = Path(result["txt"])
        raw = generated.read_bytes()
        has_bom = raw[:3] == b"\xef\xbb\xbf"
        has_crlf = b"\r\n" in raw
        text = raw.decode("utf-8-sig")
        sep_lengths = sorted({len(line) for line in text.splitlines() if line and set(line) == {"*"}})
        sep_count = sum(1 for line in text.splitlines() if line and set(line) == {"*"})
        placeholders = sorted(set(re.findall(r"\{\([A-Z0-9_]+\)\}|@/[^/\s]+/@", text)))
        url_lines = sum(1 for line in text.splitlines() if re.match(r"^https?://", line.strip()))
        inline_links = sum(1 for line in text.splitlines() if re.search(r"\(https?://", line))
        profile = result["profile"]
        ok_sep_len = EXPECTED_SEP.get(profile) in sep_lengths
        expected_text = txt_path.read_text(encoding="utf-8-sig", errors="ignore")
        expected_sep_count = sum(1 for line in expected_text.splitlines() if line and set(line) == {"*"})
        print(
            f"{html_path.name}: profile={profile} sep_lens={sep_lengths} "
            f"expected_len={EXPECTED_SEP.get(profile)} ok_len={ok_sep_len} "
            f"sep_count={sep_count} expected_sep_count={expected_sep_count} "
            f"bom={has_bom} crlf={has_crlf} stacked_urls={url_lines} inline_urls={inline_links} "
            f"placeholders={len(placeholders)} imgs={result['images_unique']}"
        )
