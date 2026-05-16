"""Procesa un HTML 'desconocido' (que no coincide con ninguna heurística de perfil)
y muestra el TXT generado + stats. El HTML está en samples/synthetic_unknown.html."""
import sys
import tempfile
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
sys.path.insert(0, str(_REPO_ROOT))

from html_export_service import export_html

SYNTHETIC = _REPO_ROOT / "samples" / "synthetic_unknown.html"

with tempfile.TemporaryDirectory() as td:
    r = export_html(
        html_file=SYNTHETIC,
        out_dir=Path(td) / "out",
        mode="clean",
        profile="auto",
        image_layout="images",
        dry_run_images=True,
    )
    txt = Path(r["txt"]).read_text(encoding="utf-8-sig")
    print(f"Profile detectado: {r['profile']}")
    print(f"Imagenes detectadas: {r['images_unique']}")
    print("=" * 60)
    print(txt)
    print("=" * 60)
    print("STATS:", r["text_stats"])
