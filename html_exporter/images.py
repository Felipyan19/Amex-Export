from __future__ import annotations

import re
from pathlib import Path
import shutil
import urllib.request
from typing import Dict

from .parser import ImageAsset


def resolve_src(src: str, html_file: Path) -> str:
    value = (src or "").strip()
    if re.match(r"^https?://", value, flags=re.IGNORECASE):
        return value
    return str((html_file.parent / value).resolve())


def download_or_copy_image(src: str, html_file: Path, out_file: Path) -> str:
    resolved = resolve_src(src, html_file)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        if re.match(r"^https?://", resolved, flags=re.IGNORECASE):
            urllib.request.urlretrieve(resolved, str(out_file))
        else:
            src_file = Path(resolved)
            if not src_file.exists():
                return f"missing-local-src:{src}"
            shutil.copy2(src_file, out_file)
        return "ok"
    except Exception as exc:
        return f"error:{exc}"


def dedupe_images_by_filename(images: list[ImageAsset]) -> Dict[str, ImageAsset]:
    unique: Dict[str, ImageAsset] = {}
    for image in images:
        if image.filename:
            unique[image.filename] = image
    return unique
