# Perfil `pp`

Platinum Concierge — campañas de Dining (Ultramarinos) y experiencias premium.

## Reglas específicas

| Aspecto | Valor |
|---|---|
| Separador | `*` × **124** |
| Link style | `stacked` |
| Heurística de detección | el HTML contiene `"ultramarino"` o `"platinum concierge"` (case insensitive) |

## Samples

- [PP-Dining-Ultramarino-Nov25-PLAT](../../samples/pp/PP-Dining-Ultramarino-Nov25-PLAT/)

## Notas

- Para reglas globales ver [../RULES.md](../RULES.md).
- Estructuralmente similar a `merchant` (mismo separador, mismo link style) — se separa para permitir futuras divergencias sin tocar el default.
- Configurado en [`html_exporter/rules.py`](../../html_exporter/rules.py).
