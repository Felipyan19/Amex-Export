# Reglas globales HTML → ZIP (html + txt + images)

Este documento define las reglas que aplica el servicio a **cualquier HTML de campaña**, sin parámetros del cliente. Las reglas son estructurales: no dependen del contenido textual ni de un nombre de campaña.

Para detalles de cada perfil ver [profiles/](profiles/). Para el workflow general ver [HTML_EXPORT_AUTOMATION.md](HTML_EXPORT_AUTOMATION.md).

---

## 1. Contrato del servicio

| Aspecto | Valor |
|---|---|
| Endpoint | `POST /export` |
| Entrada | HTML (multipart `html=@file.html` o JSON `{"html":"..."}`) |
| Parámetros | **ninguno** (sin `mode`, `profile`, `image_layout`) |
| Salida | `application/zip` con `<stem>.html` + `<stem>.txt` + `images/*` |
| Modo interno | `mode=clean`, `profile=auto`, `image_layout=images` |

---

## 2. Reglas del archivo TXT

Texto plano, listo para correo o copy-paste manual.

| Regla | Valor |
|---|---|
| Encoding | **UTF-8 con BOM** (`EF BB BF`) |
| Line endings | **CRLF** (`\r\n`) |
| Acentos | **nativos** (`María`, `¿`, `®`) — NO entidades HTML |
| Entidades HTML del input | decodificadas (`&aacute;` → `á`, `&iquest;` → `¿`) |
| Mojibake típico | normalizado: `Â®` → `(R)`, `â„¢` → `(TM)`, `Â©` → `(C)` |
| Líneas en blanco | **eliminadas** (máximo **0**) — la separación entre módulos la da la línea de asteriscos, no los blancos |
| Espacios antes de `.` o `,` | eliminados |

### 2.1 Separadores de sección

Carácter `*` repetido. El **largo** depende del perfil — ver [profiles/](profiles/).

**El separador se emite cuando**:
1. Aparece un `<hr>` en el HTML.
2. Un `<td>` o `<tr>` tiene `border-top: Xpx solid …` en su `style` (separador **antes** del bloque).
3. Un `<td>` o `<tr>` tiene `border-bottom: Xpx solid …` en su `style` (separador **después** del bloque).

Implementación: [html_exporter/parser.py](../html_exporter/parser.py) (función `_has_solid_border`).

> **Nota**: los `.txt` de muestra pueden tener separadores adicionales agregados editorialmente que no corresponden a ningún marcador estructural del HTML. No se reproducen — el servicio solo emite separadores donde el HTML los señala.

### 2.2 Links

Dos estilos según perfil:

| Estilo | Formato | Perfiles |
|---|---|---|
| `stacked` | línea 1: CTA<br>línea 2: URL | `merchant`, `mr_plat`, `pp` |
| `inline` | `CTA (URL)` en la misma línea | `mr_cent` |

### 2.3 Placeholders

Se preservan **literales** (no se decodifican, no se reemplazan):

- `{(FULLNAME)}`, `{(LAST_5)}`, `{(MEMBER_SINCE)}`, `{(URLSignature1)}`, `{(EMAIL)}`
- `@/nombre/@`, `@/MAILTARGET/@`, `@/viewonline_link/@`, `@/unsub_token/@`

Regex de reconocimiento: `\{\([A-Z0-9_]+\)\}` y `@/[^/]+/@`.

### 2.4 Elementos descartados

- `<style>`, `<script>`, `<head>` — completamente ignorados.
- Atributos de estilo CSS — descartados del output.
- `<img alt="">` con alt vacío, símbolos solitarios (`*`, `+`, `-`, `|`) o ≤1 char.

### 2.5 Manejo de bloques

| Tag HTML | Comportamiento |
|---|---|
| `<br>` | flush de línea actual |
| `<hr>` | separador de sección (ver 2.1) |
| `<p>`, `<div>`, `<td>`, `<tr>`, `<li>`, `<table>`, headings… | flush + posible blank entre bloques |
| `<a href="X">label</a>` | emit_link según link_style del perfil |
| `<img src="X" alt="Y">` | extraer filename a `images/`; emitir alt si es significativo y está fuera de `<a>` |

---

## 3. Reglas del archivo HTML dentro del ZIP

El HTML del ZIP **no es el HTML crudo del input**: se le aplica una transformación.

| Regla | Valor |
|---|---|
| Encoding | UTF-8 |
| Tags / markup | **intactos** (mismo árbol que el input) |
| `<script>` y `<style>` | contenido **intacto** (no se toca para no romper JS/CSS) |
| Contenido textual con caracteres non-ASCII | convertido a **entidades HTML** |
| Valores de atributo con caracteres non-ASCII | convertidos a entidades HTML (incluye `href`) |

### 3.1 Mapeo de entidades

Usa `html.entities.codepoint2name` (stdlib). Si hay un nombre canónico se usa, si no hay nombre se emite numérico:

| Carácter nativo | Entidad |
|---|---|
| `á` | `&aacute;` |
| `é` | `&eacute;` |
| `í` | `&iacute;` |
| `ó` | `&oacute;` |
| `ú` | `&uacute;` |
| `ñ` | `&ntilde;` |
| `¿` | `&iquest;` |
| `¡` | `&iexcl;` |
| `®` | `&reg;` |
| `©` | `&copy;` |
| `™` | `&trade;` |
| `—` | `&mdash;` |
| `–` | `&ndash;` |
| `'` | `&rsquo;` / `&lsquo;` |
| (codepoint sin nombre) | `&#NNNN;` numérico |

Implementación: [html_exporter/html_encode.py](../html_exporter/html_encode.py).

**Verificación**: después del procesamiento, el HTML dentro del ZIP debe tener **0 caracteres non-ASCII** en contenido textual y atributos.

---

## 4. Reglas de imágenes (`images/` en el ZIP)

| Regla | Valor |
|---|---|
| Fuente | atributo `src` de todos los `<img>` del HTML |
| Soporta | URLs absolutas (`https://...`) y paths relativos |
| Deduplicación | por **filename** (mismo nombre = una sola copia) |
| Ubicación en ZIP | `images/<filename>` |
| Filename extraído | parte final del path (sin query string ni fragment) |
| URLs absolutas | descargadas vía HTTP |
| Paths relativos | copiados desde el directorio del HTML de input |

### 4.1 Reescritura del `src` en el HTML del ZIP

El `src` de cada `<img>` en el HTML entregado se reescribe según `delivery_type`:

| `delivery_type` | Reescritura del `src` | Implementación |
|---|---|---|
| `centurion` | ruta **relativa** (solo el filename) — las imágenes van en root del ZIP | `_rewrite_img_srcs_to_relative` |
| otro (**marigold**) | base pública `https://i.email.americanexpress.com/wpm/1288/Images/<filename>` | `_rewrite_img_srcs_to_marigold` |

En ambos casos el filename es la parte final del path original (sin query ni fragment). Los `data:` URIs no se tocan. Implementación: [html_export_api.py](../html_export_api.py).

---

## 5. Detección automática de perfil

`profile=auto` — la heurística mira el contenido del HTML (lowercase):

| Heurística (substring match en el HTML) | Perfil resuelto |
|---|---|
| `"centurion"` + `"smiles"` | `mr_cent` |
| `"membership rewards"` + `"smiles"` | `mr_plat` |
| `"ultramarino"` o `"platinum concierge"` | `pp` |
| ninguna anterior | `merchant` (default) |

Implementación: [html_exporter/rules.py](../html_exporter/rules.py) → `detect_profile()`.

**Importante**: si una campaña futura no calza en ninguna heurística, cae a `merchant` (separador 124, stacked links) — un default razonable. Para agregar nuevos perfiles, ver `PROFILE_RULES` y `detect_profile` en `rules.py`.

---

## 6. Verificación

Ver [../scripts/](../scripts/):

- `verify_export.py` — corre el servicio sobre todos los samples y reporta stats.
- `verify_unknown.py` — procesa el HTML sintético `samples/synthetic_unknown.html` para confirmar que un HTML no mapeado funciona con reglas globales.
- `test_zip_encoding.py` — verifica que el HTML dentro del ZIP usa entidades y el TXT usa acentos nativos.
- `golden_regression.py` — compara TXT generado vs TXT esperado de cada sample y reporta similitud.
