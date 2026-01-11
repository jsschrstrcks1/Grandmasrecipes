# Recipe Transcription Skill

**Purpose:** Transcribe handwritten recipe cards with maximum accuracy and fidelity to the original source.

**Activation:** This skill activates when reading images from `data/` or `data/processed/` directories, or when keywords like "transcribe", "OCR", "handwritten", or "recipe card" appear.

---

## Core Principles

### 1. Accuracy Over Speed
These are irreplaceable family heirlooms. Take time to get it right.

### 2. Fidelity to Source
Preserve grandma's exact wording, spelling, and style. Do NOT:
- "Correct" her spelling
- Modernize her language
- Standardize her formatting
- Add steps she didn't write

### 3. Honesty About Uncertainty
When you can't read something clearly:
- Use `[UNCLEAR]` marker
- Optionally note possibilities: `[UNCLEAR: possibly "1/2" or "1/4"]`
- NEVER guess or invent

---

## Pre-Transcription Checklist

Before reading any image:

```bash
# 1. Check image dimensions (must be ≤2000px)
python scripts/image_safeguards.py status

# 2. Use processed version if available
# PREFER: data/processed/filename.jpeg
# AVOID:  data/filename.jpeg (may be oversized)
```

---

## OCR Correction Standards

### Character Confusion (Watch For)

| Often Misread As | Should Be | Context |
|------------------|-----------|---------|
| `l` (lowercase L) | `1` (one) | In numbers: `l cup` → `1 cup` |
| `1` (one) | `l` (lowercase L) | In words: `mi1k` → `milk` |
| `O` (letter O) | `0` (zero) | In temperatures: `35O°F` → `350°F` |
| `0` (zero) | `O` (letter O) | In words: `0ven` → `Oven` |
| `rn` | `m` | In words: `warrn` → `warm` |
| `cl` | `d` | In words: `acld` → `add` |

### Critical Measurement Distinctions

| IF YOU READ | DOUBLE-CHECK | WHY |
|-------------|--------------|-----|
| `tbsp` | Could be `tsp`? | 3x difference in quantity! |
| `tsp` | Could be `tbsp`? | 3x difference in quantity! |
| `1/4` | Could be `1/2`? | 2x difference |
| `oz` | Could be `fl oz`? | Weight vs volume |

### Measurement Standardization

Use these abbreviations consistently:
- **Volume:** tsp, tbsp, cup, fl oz, pt, qt, gal
- **Weight:** oz, lb
- **Temperature:** Dual format `350°F (175°C)`
- **Time:** min, hr (or spell out)

---

## Transcription Output Format

```json
{
  "id": "recipe-slug-from-title",
  "collection": "grandma-baker",
  "collection_display": "Grandma Baker",
  "title": "Exact Title From Card",
  "category": "desserts",
  "image_refs": ["Grandmas-recipes - XX.jpeg"],
  "ingredients": [
    "2 cups flour",
    "1 tsp salt",
    "[UNCLEAR] sugar"
  ],
  "instructions": [
    "Mix dry ingredients",
    "Add wet ingredients",
    "[UNCLEAR: possibly 'fold' or 'stir'] gently"
  ],
  "notes": [
    "Transcription confidence: high/medium/low",
    "Image quality issues: [describe if any]"
  ],
  "confidence": "high"
}
```

---

## Confidence Ratings

| Rating | Criteria |
|--------|----------|
| `high` | All text clearly readable, no guessing required |
| `medium` | 1-3 unclear words, marked with `[UNCLEAR]` |
| `low` | Significant portions unclear, multiple `[UNCLEAR]` markers |

---

## Guardrails

### MUST DO:
- Use `[UNCLEAR]` for any text you cannot read with certainty
- Preserve original spelling and grammar
- Note image quality issues in recipe notes
- Use processed images (≤2000px) when available
- Run validation after adding recipe: `python scripts/validate-recipes.py`

### MUST NOT:
- Invent ingredients, steps, or measurements
- Guess what unclear text says
- "Improve" or modernize grandma's wording
- Delete or modify handwritten image files
- Skip the image dimension check

---

## Post-Transcription Validation

After transcribing:

```bash
# Validate the recipe was added correctly
python scripts/validate-recipes.py

# Check for common issues:
# - Missing required fields (id, title, ingredients, instructions, category)
# - Invalid category
# - Suspicious measurements (too much salt, etc.)
```

---

## Resources

- [OCR Correction Standards](../../CLAUDE.md#ocr-correction-standards)
- [Recipe Schema](../../CLAUDE.md#recipe-schema)
- [Valid Categories](../../CLAUDE.md#categories)

---

*"Accuracy is more important than speed. These recipes matter deeply to this family."*
