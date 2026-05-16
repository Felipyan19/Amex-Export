from html_exporter.service import (
    detect_profile,
    export_html,
    extract_filename_from_src,
    fix_url,
    main,
)

__all__ = [
    "detect_profile",
    "export_html",
    "extract_filename_from_src",
    "fix_url",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
