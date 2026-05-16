# Perfil `mr_cent`

Centurion + Smiles. Único perfil con link style `inline`.

## Reglas específicas

| Aspecto | Valor |
|---|---|
| Separador | `*` × **99** |
| Link style | **`inline`** — `CTA (URL)` en la misma línea |
| Heurística de detección | el HTML contiene `"centurion"` **y** `"smiles"` (case insensitive) |

## Samples

- [MR-Bonus-Smiles-Dic25-CENT](../../samples/mr_cent/MR-Bonus-Smiles-Dic25-CENT/)

## Ejemplo de link inline

```
Mi cuenta (https://www.americanexpress.com/es-ar/account/login?email_consumer)
```

vs stacked (otros perfiles):

```
Mi cuenta
https://www.americanexpress.com/es-ar/account/login?email_consumer
```

## Notas

- Para reglas globales ver [../RULES.md](../RULES.md).
- Los placeholders `@/.../@` aparecen frecuentemente en este perfil (formato Membership-Rewards/Centurion).
- Configurado en [`html_exporter/rules.py`](../../html_exporter/rules.py) como `link_style="inline"`.
