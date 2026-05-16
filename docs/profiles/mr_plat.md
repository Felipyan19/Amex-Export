# Perfil `mr_plat`

Membership Rewards + Smiles (Platinum tier).

## Reglas específicas

| Aspecto | Valor |
|---|---|
| Separador | `*` × **98** |
| Link style | `stacked` |
| Heurística de detección | el HTML contiene `"membership rewards"` **y** `"smiles"` (case insensitive) |

## Samples

- [MR-Bonus-Smiles-Dic25-PLAT](../../samples/mr_plat/MR-Bonus-Smiles-Dic25-PLAT/)

## Notas

- Para reglas globales ver [../RULES.md](../RULES.md).
- Si el HTML matchea también `"centurion"`, gana `mr_cent` (más específico).
- Configurado en [`html_exporter/rules.py`](../../html_exporter/rules.py).
