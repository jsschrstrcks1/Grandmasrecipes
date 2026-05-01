# OCR Correction Standards — Grandma's Kitchen

Use this when transcribing handwritten recipe cards.

## Character Confusion

| Misread | Correct | Context |
|---|---|---|
| `l` | `1` | Numbers (`l cup` → `1 cup`) |
| `1` | `l` | Words (`mi1k` → `milk`) |
| `O` | `0` | Numbers (`35O°F` → `350°F`) |
| `0` | `O` | Words (`0ven` → `Oven`) |
| `rn` | `m` | r-n combination vs letter m |
| `cl` | `d` | c-l combination vs letter d |

## CRITICAL: Measurement Distinctions

| DANGEROUS | CORRECT | Impact |
|---|---|---|
| `tbsp` | `tsp` | 3× difference |
| `tsp` | `tbsp` | 3× difference |
| `cup` | `cups` | Quantity matters |
| `oz` | `fl oz` | Weight vs volume |

## Standardized Abbreviations

- **Volume:** tsp, tbsp, cup, fl oz, pt, qt, gal
- **Weight:** oz, lb
- **Temperature:** dual format — `350°F (175°C)`

## When Uncertain

- Mark `[UNCLEAR]` — never guess.
- Note possible readings: `[UNCLEAR: possibly "1/2" or "1/4"]`.
- Flag for human review in recipe `notes`.
