# Image Workflow — Grandma's Kitchen

## Handwritten images are sacred

Grandma Baker's handwritten recipe cards are **irreplaceable family heirlooms**.

| Image type | Action |
|---|---|
| Handwritten recipe cards | **NEVER DELETE** — preserve, optimize, display |
| Typed / printed recipes | May delete after JSON ingestion |
| Magazine clippings | May delete after JSON ingestion |

## CRITICAL: Image Path Structure

Images are **flat** in `data/`. No subdirectories.

```
CORRECT:   data/Grandmas-recipes - 12.jpeg
WRONG:     data/grandma/Grandmas-recipes - 12.jpeg
```

The `getCollectionImagePath()` function in `script.js` returns `'data/'` for local images.

## Two API limits to respect

### 1. 2000 px per image

Original iPhone photos run up to 4032 × 3024 px. Always read from `data/processed/`.

```bash
python scripts/process_images.py            # Resize originals → ≤2000 px copies
python scripts/image_safeguards.py status
```

### 2. 100 images per request

Exceeding it errors:

```
Too much media: 0 document pages + 101 images > 100
```

- Never batch-process more than 100 images at once.
- Use `image_safeguards.py get_batches()` for safe batching.
- Process one-by-one when possible.

## Manifest Commands

```bash
# Status
python scripts/image_safeguards.py status

# Validate (creates / refreshes manifest)
python scripts/image_safeguards.py validate

# Get next unprocessed
python scripts/image_safeguards.py next grandma-baker

# Mark images
python scripts/image_safeguards.py mark "file.jpeg" processed
python scripts/image_safeguards.py mark "file.jpeg" skipped "Not a recipe"

# List broken
python scripts/image_safeguards.py broken
```

## Status Values

| Status | Meaning |
|---|---|
| `valid` | Ready to process |
| `oversized` | Valid but >2000 px (use processed version) |
| `resized` | Processed version available |
| `broken` | Cannot read (skip) |
| `recoverable` | Partially corrupted (may work) |
| `processed` | Recipe extraction complete |
| `skipped` | Not a recipe |
