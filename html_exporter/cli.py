from __future__ import annotations

import argparse

from .core import run_exports


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Exporta HTML de campana a TXT + imagenes con reglas estables."
    )
    parser.add_argument("--input", required=True, help="Archivo o carpeta de entrada")
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Carpeta de salida. Si no se indica, usa la carpeta del HTML.",
    )
    parser.add_argument(
        "--mode",
        choices=["legacy", "clean"],
        default="legacy",
        help="legacy replica estilo anterior; clean corrige urls y normaliza.",
    )
    parser.add_argument(
        "--profile",
        choices=["auto", "merchant", "mr_plat", "mr_cent", "pp"],
        default="auto",
    )
    parser.add_argument(
        "--image-layout",
        choices=["images", "root"],
        default="images",
        help="Ubicacion de imagenes: subcarpeta images o raiz.",
    )
    parser.add_argument("--txt-name", default=None, help="Nombre de TXT para modo 1 archivo")
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Si input es carpeta, procesa todos los .html recursivamente.",
    )
    parser.add_argument(
        "--log-json",
        default="export_log.json",
        help="Nombre del log JSON por campana (se guarda dentro de cada out_dir). Use empty para desactivar.",
    )
    parser.add_argument(
        "--summary-json",
        default=None,
        help="Ruta de JSON resumen global para corrida batch/single.",
    )
    parser.add_argument(
        "--dry-run-images",
        action="store_true",
        help="No descarga/copia imagenes, solo reporta.",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.log_json == "":
        args.log_json = None

    return run_exports(args)
