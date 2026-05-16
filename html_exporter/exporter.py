from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import sys

from .images import dedupe_images_by_filename, download_or_copy_image
from .parser import EmailHTMLToTextParser
from .postprocess import collect_text_stats, postprocess_lines
from .rules import detect_profile, get_rules


def export_html(
    html_file: Path,
    out_dir: Path,
    mode: str = "legacy",
    profile: str = "auto",
    image_layout: str = "images",
    txt_name: Optional[str] = None,
    dry_run_images: bool = False,
) -> dict:
    html_text = html_file.read_text(encoding="utf-8", errors="ignore")
    resolved_profile = detect_profile(html_text) if profile == "auto" else profile
    rules = get_rules(resolved_profile)

    parser = EmailHTMLToTextParser(mode=mode, rules=rules)
    parser.feed(html_text)
    lines, images, warnings = parser.finalize()
    lines = postprocess_lines(lines, rules, mode)
    stats = collect_text_stats(lines)

    out_dir.mkdir(parents=True, exist_ok=True)
    txt_filename = txt_name or f"{html_file.stem}.txt"
    txt_path = out_dir / txt_filename

    with txt_path.open("w", encoding="utf-8-sig", newline="\r\n") as file:
        file.write("\r\n".join(lines) + "\r\n")

    image_dir = out_dir if image_layout == "root" else out_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    unique_images = dedupe_images_by_filename(images)

    image_results = []
    for filename, asset in sorted(unique_images.items()):
        out_file = image_dir / filename
        status = "skipped-dry-run" if dry_run_images else download_or_copy_image(asset.src, html_file, out_file)
        image_results.append(
            {
                "filename": filename,
                "src": asset.src,
                "alt": asset.alt,
                "path": str(out_file),
                "status": status,
            }
        )

    return {
        "html": str(html_file),
        "txt": str(txt_path),
        "profile": resolved_profile,
        "mode": mode,
        "rules": asdict(rules),
        "text_stats": stats,
        "warnings": warnings,
        "images_total_tags": len(images),
        "images_unique": len(unique_images),
        "images_saved": len([x for x in image_results if x["status"] == "ok"]),
        "image_results": image_results,
    }


def find_html_files(input_path: Path, batch: bool) -> List[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() != ".html":
            raise ValueError("El archivo de entrada debe ser .html")
        return [input_path]
    if not input_path.is_dir():
        raise ValueError("La ruta de entrada no existe")
    if batch:
        return sorted(input_path.rglob("*.html"))
    htmls = sorted(input_path.glob("*.html"))
    return htmls if htmls else sorted(input_path.rglob("*.html"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def run_exports(args: argparse.Namespace) -> int:
    input_path = Path(args.input).resolve()
    html_files = find_html_files(input_path, args.batch)
    if not html_files:
        print("No se encontraron archivos .html")
        return 1

    print(f"HTML encontrados: {len(html_files)}")
    failures = 0
    results = []

    for html_file in html_files:
        if args.out_dir:
            out_dir = Path(args.out_dir).resolve() if len(html_files) == 1 else Path(args.out_dir).resolve() / html_file.stem
        else:
            out_dir = html_file.parent

        try:
            result = export_html(
                html_file=html_file,
                out_dir=out_dir,
                mode=args.mode,
                profile=args.profile,
                image_layout=args.image_layout,
                txt_name=args.txt_name if len(html_files) == 1 else None,
                dry_run_images=args.dry_run_images,
            )
            results.append(result)
            print(
                f"[OK] {html_file.name} -> {Path(result['txt']).name} | "
                f"imgs: {result['images_saved']}/{result['images_unique']} | "
                f"profile={result['profile']} | url_lines={result['text_stats']['url_lines']}"
            )

            if args.log_json:
                log_path = out_dir / args.log_json
                write_json(log_path, {"timestamp_utc": now_iso(), "result": result})
        except Exception as exc:
            failures += 1
            print(f"[ERROR] {html_file}: {exc}", file=sys.stderr)

    if args.summary_json:
        summary_path = Path(args.summary_json).resolve()
        by_profile: Dict[str, int] = {}
        for result in results:
            prof = result["profile"]
            by_profile[prof] = by_profile.get(prof, 0) + 1

        write_json(
            summary_path,
            {
                "timestamp_utc": now_iso(),
                "input": str(input_path),
                "mode": args.mode,
                "profile_arg": args.profile,
                "batch": args.batch,
                "processed": len(results),
                "failures": failures,
                "by_profile": by_profile,
                "results": results,
            },
        )

    if failures:
        print(f"Finalizado con errores: {failures}")
        return 2

    print("Finalizado sin errores.")
    return 0
