from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import Optional
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile  # noqa: F401
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from html_export_service import export_html
from html_exporter.html_encode import encode_html_special_chars

FIXED_MODE = "clean"
FIXED_PROFILE = "auto"
FIXED_IMAGE_LAYOUT = "images"


class ExportJsonPayload(BaseModel):
    html: str = Field(
        ...,
        min_length=1,
        description="Contenido HTML",
    )
    artifact_name: str = Field(
        ...,
        description="Nombre del archivo de salida (auto agrega .html si no lo tiene)",
    )
    delivery_type: str = Field(
        ...,
        description="'centurion' = images en root del ZIP, otro valor = images en images/",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "html": "<html><body><h1>Statement</h1></body></html>",
                "artifact_name": "amex_statement.html",
                "delivery_type": "centurion",
            }
        }
    }


app = FastAPI(
    title="HTML Export API",
    version="2.0.0",
    description=(
        "API para exportar HTML a ZIP (html + txt + images).\n\n"
        "El endpoint `/export/zip` acepta **dos formatos**:\n"
        "- `application/json` — campos: `html`, `artifact_name`, `delivery_type`\n"
        "- `multipart/form-data` — campos: `html` (archivo .html), `artifact_name`, `delivery_type`"
    ),
    contact={
        "name": "Amex Export Service",
        "url": "http://149.130.164.187:5088",
    },
    license_info={"name": "Internal Use"},
    openapi_tags=[
        {"name": "Export", "description": "Exportación HTML a ZIP"},
        {"name": "Info", "description": "Información del servicio"},
        {"name": "Monitoring", "description": "Health check y monitoreo"},
    ],
)


def _safe_html_name(name: Optional[str]) -> str:
    if not name:
        return "input.html"
    base = Path(name).name
    if not base:
        return "input.html"
    if not base.lower().endswith(".html"):
        base = f"{base}.html"
    return base


def _resolve_image_layout(delivery_type: Optional[str]) -> str:
    if delivery_type and delivery_type.strip().lower() == "centurion":
        return "root"
    return "images"


def _build_zip(html_bytes: bytes, filename: str, image_layout: str = FIXED_IMAGE_LAYOUT) -> tuple[bytes, str]:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        html_path = root / filename
        html_path.write_bytes(html_bytes)

        out_dir = root / "out"
        result = export_html(
            html_file=html_path,
            out_dir=out_dir,
            mode=FIXED_MODE,
            profile=FIXED_PROFILE,
            image_layout=image_layout,
            dry_run_images=False,
        )

        zip_name = f"{html_path.stem}_export.zip"
        zip_path = root / zip_name

        try:
            raw_html_text = html_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raw_html_text = html_bytes.decode("utf-8", errors="replace")
        encoded_html_text = encode_html_special_chars(raw_html_text)

        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zf:
            zf.writestr(html_path.name, encoded_html_text.encode("utf-8"))
            txt_path = Path(result["txt"])
            if txt_path.exists():
                zf.write(txt_path, arcname=txt_path.name)

            images_dir = out_dir if image_layout == "root" else out_dir / "images"
            if images_dir.exists():
                for file in images_dir.rglob("*"):
                    if file.is_file() and file.suffix.lower() != ".txt":
                        rel = file.relative_to(out_dir)
                        zf.write(file, arcname=str(rel).replace("\\", "/"))

        return zip_path.read_bytes(), zip_name


_ZIP_RESPONSES = {
    200: {
        "description": "ZIP generado exitosamente",
        "content": {"application/zip": {}},
        "headers": {
            "Content-Disposition": {
                "description": 'attachment; filename="{name}_export.zip"',
                "schema": {"type": "string"},
            }
        },
    },
    400: {
        "description": "Error en request",
        "content": {
            "application/json": {
                "examples": {
                    "empty_html": {"value": {"error": "HTML vacio"}},
                    "invalid_data": {"value": {"error": "Datos invalidos"}},
                }
            }
        },
    },
    500: {
        "description": "Error interno",
        "content": {"application/json": {"example": {"error": "Error interno: ..."}}},
    },
}


@app.get("/", tags=["Info"], summary="Service info")
def root() -> dict:
    return {
        "service": "html-export-api",
        "version": "2.0.0",
        "endpoints": {"export": "POST /export/zip (application/json o multipart/form-data)"},
        "returns": "application/zip (html + txt + images/)",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Monitoring"], summary="Health check")
def health() -> dict:
    return {"ok": True}


@app.post(
    "/export/zip",
    tags=["Export"],
    summary="Exportar HTML a ZIP",
    description=(
        "Exporta HTML a ZIP. Acepta dos formatos según el `Content-Type`:\n\n"
        "- **application/json** — campos: `html` (string), `artifact_name`, `delivery_type`\n"
        "- **multipart/form-data** — campos: `html` (archivo .html), `artifact_name`, `delivery_type`"
    ),
    response_description="ZIP file",
    responses=_ZIP_RESPONSES,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["html", "artifact_name", "delivery_type"],
                        "properties": {
                            "html": {
                                "type": "string",
                                "minLength": 1,
                                "description": "Contenido HTML",
                                "example": "<html><body><h1>Statement</h1></body></html>",
                            },
                            "artifact_name": {
                                "type": "string",
                                "description": "Nombre del archivo de salida (auto agrega .html si no lo tiene)",
                                "example": "amex_statement.html",
                            },
                            "delivery_type": {
                                "type": "string",
                                "description": "'centurion' = images en root del ZIP, otro valor = images en images/",
                                "example": "centurion",
                            },
                        },
                    },
                    "example": {
                        "html": "<html><body><h1>Statement</h1></body></html>",
                        "artifact_name": "amex_statement.html",
                        "delivery_type": "centurion",
                    },
                },
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["html", "artifact_name", "delivery_type"],
                        "properties": {
                            "html": {
                                "type": "string",
                                "format": "binary",
                                "description": "Archivo HTML a exportar",
                            },
                            "artifact_name": {
                                "type": "string",
                                "description": "Nombre del archivo de salida",
                                "example": "amex_statement.html",
                            },
                            "delivery_type": {
                                "type": "string",
                                "description": "'centurion' = images en root, otro = images en images/",
                                "example": "centurion",
                            },
                        },
                    }
                },
            },
        }
    },
)
async def export_endpoint(
    request: Request,
    html: Optional[UploadFile] = File(None),
    artifact_name: Optional[str] = Form(None),
    delivery_type: Optional[str] = Form(None),
) -> Response:
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("application/json"):
        raw = await request.body()
        if not raw:
            raise HTTPException(status_code=400, detail="Body vacio")
        try:
            payload = ExportJsonPayload.model_validate_json(raw)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"JSON invalido: {exc}")
        filename = _safe_html_name(payload.artifact_name)
        html_bytes = payload.html.encode("utf-8")
        image_layout = _resolve_image_layout(payload.delivery_type)
    else:
        if html is None:
            raise HTTPException(status_code=400, detail="Falta campo html (archivo)")
        if not artifact_name:
            raise HTTPException(status_code=400, detail="Falta campo artifact_name")
        if not delivery_type:
            raise HTTPException(status_code=400, detail="Falta campo delivery_type")
        html_bytes = await html.read()
        if not html_bytes:
            raise HTTPException(status_code=400, detail="Archivo html vacio")
        filename = _safe_html_name(artifact_name)
        image_layout = _resolve_image_layout(delivery_type)

    try:
        zip_bytes, zip_name = _build_zip(html_bytes=html_bytes, filename=filename, image_layout=image_layout)
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error interno: {exc}")


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


def main() -> int:
    parser = argparse.ArgumentParser(description="FastAPI para exportar HTML -> ZIP (html + txt + images)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--certfile", default=None, help="Certificado PEM para HTTPS")
    parser.add_argument("--keyfile", default=None, help="Key PEM para HTTPS")
    args = parser.parse_args()

    if args.keyfile and not args.certfile:
        raise SystemExit("Si envias --keyfile tambien debes enviar --certfile")

    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit("Falta dependencia: uvicorn. Instala con `pip install uvicorn fastapi python-multipart`.") from exc

    uvicorn.run(
        "html_export_api:app",
        host=args.host,
        port=args.port,
        ssl_certfile=args.certfile,
        ssl_keyfile=args.keyfile,
        reload=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
