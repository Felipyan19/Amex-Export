# Perfil `merchant`

Default. Cae acá cualquier HTML que no matchee otras heurísticas.

## Reglas específicas

| Aspecto | Valor |
|---|---|
| Separador | `*` × **124** |
| Link style | `stacked` (CTA en línea 1, URL en línea 2) |
| Heurística de detección | ninguna explícita — es el default |

## Samples

- [MERCHANT-Newsletter-Dic25](../../samples/merchant/MERCHANT-Newsletter-Dic25/)
- [MERCHANT-SHOT-Navidad-Dic25](../../samples/merchant/MERCHANT-SHOT-Navidad-Dic25/)

## Notas

- Para reglas globales (BOM, CRLF, placeholders, encoding HTML, imágenes), ver [../RULES.md](../RULES.md).
- Configurado en [`html_exporter/rules.py`](../../html_exporter/rules.py) como `ExportRules(separator_length=124, link_style="stacked")`.
