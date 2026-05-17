from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import Optional
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from html_export_service import export_html
from html_exporter.html_encode import encode_html_special_chars

FIXED_MODE = "clean"
FIXED_PROFILE = "auto"
FIXED_IMAGE_LAYOUT = "images"


class ExportJsonPayload(BaseModel):
    """JSON payload para exportación"""

    html: str = Field(
        ...,
        min_length=1,
        description="Contenido HTML",
        json_schema_extra={
            "example": "<html><body><h1>Title</h1><p>Content</p></body></html>"
        }
    )
    filename: Optional[str] = Field(
        default="input.html",
        description="Nombre archivo (auto agrega .html)",
        json_schema_extra={"example": "report.html"}
    )
    artifact_name: Optional[str] = Field(
        default=None,
        description="Nombre alternativo (prioridad sobre filename)",
        json_schema_extra={"example": "statement.html"}
    )
    delivery_type: Optional[str] = Field(
        default=None,
        description="'centurion' = images en root, otro = images en images/",
        json_schema_extra={"example": "centurion"}
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "html": "<html><body><h1>Report</h1></body></html>",
                    "filename": "report.html"
                },
                {
                    "html": "<html><body><h1>Statement</h1><img src='data:image/png;base64,iVBORw0...' /></body></html>",
                    "artifact_name": "amex_statement.html",
                    "delivery_type": "centurion"
                }
            ]
        }
    }


app = FastAPI(
    title="HTML Export API",
    version="2.0.0",
    description="API para exportar HTML a ZIP (html + txt + images). Acepta JSON y multipart/form-data.",
    contact={
        "name": "Amex Export Service",
        "url": "http://149.130.164.187:5088",
    },
    license_info={
        "name": "Internal Use",
    },
    openapi_tags=[
        {
            "name": "Export",
            "description": "Endpoints de exportación HTML a ZIP"
        },
        {
            "name": "Info",
            "description": "Información del servicio"
        },
        {
            "name": "Monitoring",
            "description": "Health check y monitoreo"
        }
    ]
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


@app.get(
    "/",
    tags=["Info"],
    summary="Service info",
    description="Retorna info del servicio en JSON"
)
def root() -> dict:
    return {
        "service": "html-export-api",
        "version": "2.0.0",
        "endpoints": {
            "json": "POST /export/json (application/json)",
            "multipart": "POST /export/zip (multipart/form-data)"
        },
        "returns": "application/zip (html + txt + images/)",
        "docs": "/docs",
        "health": "/health",
    }


@app.get(
    "/health",
    tags=["Monitoring"],
    summary="Health check",
    description="Retorna {\"ok\": true} si el servicio está operativo"
)
def health() -> dict:
    return {"ok": True}


@app.post(
    "/export/json",
    tags=["Export"],
    summary="Exportar HTML a ZIP (JSON)",
    description="Endpoint JSON para exportar HTML a ZIP. Acepta payload JSON con html, filename, artifact_name y delivery_type",
    response_description="ZIP file",
    responses={
        200: {
            "description": "ZIP generado exitosamente",
            "content": {"application/zip": {}},
            "headers": {
                "Content-Disposition": {
                    "description": "attachment; filename=\"{name}_export.zip\"",
                    "schema": {"type": "string"}
                }
            }
        },
        400: {
            "description": "Error en request",
            "content": {
                "application/json": {
                    "examples": {
                        "empty_html": {"value": {"error": "HTML vacio"}},
                        "invalid_data": {"value": {"error": "Datos invalidos"}}
                    }
                }
            }
        },
        500: {
            "description": "Error interno",
            "content": {
                "application/json": {
                    "example": {"error": "Error interno: ..."}
                }
            }
        }
    }
)
async def export_json_endpoint(
    payload: ExportJsonPayload = Body(
        ...,
        examples=[
            {
                "html": "<html><body><h1>Report</h1></body></html>",
                "filename": "report.html"
            },
            {
                "html": "<html><body><h1>Statement</h1><img src='data:image/png;base64,iVBORw0...' /></body></html>",
                "artifact_name": "amex_statement.html",
                "delivery_type": "centurion"
            }
        ]
    )
) -> Response:
    """Endpoint específico para JSON payload"""
    try:
        filename = _safe_html_name(payload.artifact_name or payload.filename)
        html_bytes = payload.html.encode("utf-8")
        image_layout = _resolve_image_layout(payload.delivery_type)

        zip_bytes, zip_name = _build_zip(html_bytes=html_bytes, filename=filename, image_layout=image_layout)
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error interno: {exc}")


@app.post(
    "/export/zip",
    tags=["Export"],
    summary="Exportar HTML a ZIP (multipart)",
    description="Endpoint multipart/form-data para exportar HTML a ZIP. Acepta archivos HTML o texto",
    response_description="ZIP file",
    responses={
        200: {
            "description": "ZIP generado exitosamente",
            "content": {"application/zip": {}},
            "headers": {
                "Content-Disposition": {
                    "description": "attachment; filename=\"{name}_export.zip\"",
                    "schema": {"type": "string"}
                }
            }
        },
        400: {
            "description": "Error en request",
            "content": {
                "application/json": {
                    "examples": {
                        "empty_body": {"value": {"error": "Body vacio"}},
                        "invalid_json": {"value": {"error": "JSON invalido: ..."}},
                        "empty_html": {"value": {"error": "Archivo html vacio"}}
                    }
                }
            }
        },
        500: {
            "description": "Error interno",
            "content": {
                "application/json": {
                    "example": {"error": "Error interno: ..."}
                }
            }
        }
    }
)
async def export_endpoint(
    request: Request,
    html_file: Optional[UploadFile] = File(
        None,
        alias="html",
        description="Archivo HTML a exportar (multipart/form-data)"
    ),
    html_text: Optional[str] = Form(
        None,
        description="Contenido HTML como texto (multipart/form-data)"
    ),
    filename_form: Optional[str] = Form(
        None,
        alias="filename",
        description="Nombre del archivo de salida (multipart/form-data)"
    ),
) -> Response:
    content_type = request.headers.get("content-type", "")

    try:
        if content_type.startswith("application/json"):
            raw = await request.body()
            if not raw:
                raise HTTPException(status_code=400, detail="Body vacio")
            try:
                payload = ExportJsonPayload.model_validate_json(raw)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"JSON invalido: {exc}")

            filename = _safe_html_name(payload.artifact_name or payload.filename)
            html_bytes = payload.html.encode("utf-8")
            image_layout = _resolve_image_layout(payload.delivery_type)
        else:
            image_layout = FIXED_IMAGE_LAYOUT
            filename = _safe_html_name(filename_form or getattr(html_file, "filename", None))

            if html_file is not None:
                html_bytes = await html_file.read()
            elif html_text:
                html_bytes = html_text.encode("utf-8")
            else:
                raise HTTPException(status_code=400, detail="Falta campo html (file) o html_text en multipart/form-data")

            if not html_bytes:
                raise HTTPException(status_code=400, detail="Archivo html vacio")

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
