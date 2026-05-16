# HTML Export Service

Servicio HTTP que recibe un HTML de campaña y devuelve un ZIP con:

- `<stem>.html` — el HTML original con caracteres especiales convertidos a entidades HTML (`á` → `&aacute;`, `ñ` → `&ntilde;`, `¿` → `&iquest;`, `®` → `&reg;`, etc.).
- `<stem>.txt` — texto plano con acentos nativos, encoding UTF-8 + BOM + CRLF, separadores por perfil.
- `images/` — todos los `<img src>` extraídos (URLs absolutas descargadas, relativas copiadas), deduplicados por filename.

**El cliente no envía opciones.** El servicio detecta el perfil automáticamente y aplica reglas globales.

---

## Estructura del repo

```
exports/
├── README.md                          ← estás acá
│
├── docs/
│   ├── RULES.md                       ← reglas globales del TXT, HTML y ZIP
│   ├── HTML_EXPORT_AUTOMATION.md      ← workflow general (legacy)
│   └── profiles/
│       ├── merchant.md
│       ├── mr_plat.md
│       ├── mr_cent.md
│       └── pp.md
│
├── samples/                           ← ejemplos por perfil (golden fixtures)
│   ├── merchant/
│   │   ├── MERCHANT-Newsletter-Dic25/
│   │   │   ├── MERCHANT-Newsletter-Dic25.html
│   │   │   ├── MERCHANT-Newsletter-Dic25.txt
│   │   │   └── images/
│   │   └── MERCHANT-SHOT-Navidad-Dic25/
│   ├── mr_plat/
│   │   └── MR-Bonus-Smiles-Dic25-PLAT/
│   ├── mr_cent/
│   │   └── MR-Bonus-Smiles-Dic25-CENT/
│   ├── pp/
│   │   └── PP-Dining-Ultramarino-Nov25-PLAT/
│   └── synthetic_unknown.html         ← HTML que no matchea ninguna heurística
│
├── scripts/
│   ├── verify_export.py               ← stats por sample
│   ├── verify_unknown.py              ← prueba con HTML no mapeado
│   ├── test_zip_encoding.py           ← verifica encoding HTML vs TXT en el ZIP
│   └── golden_regression.py           ← comparación TXT generado vs esperado
│
├── html_exporter/                     ← paquete core
│   ├── rules.py                       ← perfiles + detect_profile
│   ├── parser.py                      ← HTML → líneas TXT
│   ├── postprocess.py                 ← normalización genérica del TXT
│   ├── exporter.py                    ← orquesta export_html
│   ├── images.py                      ← extracción/dedup de imágenes
│   ├── html_encode.py                 ← acentos → entidades HTML para el ZIP
│   ├── cli.py
│   └── service.py
│
├── html_export_api.py                 ← FastAPI POST /export
├── html_export_service.py             ← reexport CLI
└── test_html_export_service.py        ← unit tests
```

---

## Quick start

### Servidor

```powershell
python .\html_export_api.py --host 127.0.0.1 --port 8080
```

### POST con un HTML

```powershell
curl.exe -X POST "http://127.0.0.1:8080/export" `
  -F "html=@samples\merchant\MERCHANT-Newsletter-Dic25\MERCHANT-Newsletter-Dic25.html" `
  -o "out.zip"
Expand-Archive out.zip out\
```

### Verificación rápida

```powershell
python .\scripts\verify_export.py       # stats sobre los 5 samples
python .\scripts\verify_unknown.py      # prueba HTML no mapeado
python .\scripts\test_zip_encoding.py   # encoding HTML vs TXT
python .\scripts\golden_regression.py   # similitud vs samples
```

### Tests

```powershell
python -m unittest test_html_export_service -v
```

---

## Perfiles

| Perfil | Separador | Link style | Heurística | Doc |
|---|---|---|---|---|
| `merchant` | `*` × 124 | stacked | default | [docs/profiles/merchant.md](docs/profiles/merchant.md) |
| `mr_plat` | `*` × 98 | stacked | `"membership rewards" + "smiles"` | [docs/profiles/mr_plat.md](docs/profiles/mr_plat.md) |
| `mr_cent` | `*` × 99 | **inline** | `"centurion" + "smiles"` | [docs/profiles/mr_cent.md](docs/profiles/mr_cent.md) |
| `pp` | `*` × 124 | stacked | `"ultramarino"` o `"platinum concierge"` | [docs/profiles/pp.md](docs/profiles/pp.md) |

---

## Para agregar una nueva campaña como sample

1. Crear carpeta `samples/<perfil>/<NombreCampaña>/`.
2. Adentro: `<NombreCampaña>.html`, `<NombreCampaña>.txt` (esperado), `images/` (assets).
3. Correr `python .\scripts\golden_regression.py` para confirmar similitud.

## Para agregar un nuevo perfil

1. Agregar entrada en `PROFILE_RULES` en [html_exporter/rules.py](html_exporter/rules.py).
2. Agregar heurística en `detect_profile()` en el mismo archivo.
3. Crear `docs/profiles/<perfil>.md` con sus reglas específicas.
4. Agregar la fila en la tabla de perfiles de este README.
5. Agregar carpeta `samples/<perfil>/` con al menos 1 ejemplo.

---

## Documentación

- **Empezar acá**: [docs/RULES.md](docs/RULES.md) — todas las reglas globales (TXT, HTML, imágenes, encoding, detección de perfil, separadores).
- **Por perfil**: [docs/profiles/](docs/profiles/).
- **Workflow / CLI legacy**: [docs/HTML_EXPORT_AUTOMATION.md](docs/HTML_EXPORT_AUTOMATION.md).
