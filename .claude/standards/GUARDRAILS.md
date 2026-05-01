# Guardrails — Grandma's Kitchen

## Accept vs Reject

| ✅ ACCEPT | ❌ REJECT |
|---|---|
| Verbatim transcription from source | Inventing missing ingredients or steps |
| `[UNCLEAR]` for unreadable text | Guessing measurements or quantities |
| Preserving grandma's exact wording | "Improving" or modernizing her text |
| Notes about image quality issues | Deleting ANY handwritten image |
| Marking uncertain readings | Assuming what a smudged word says |
| Original spelling and grammar | "Correcting" her personal style |
| Flat image paths in `data/` | Creating subdirectories for images |

## Don't

1. Delete handwritten images — **EVER** (irreplaceable).
2. Invent ingredients, steps, or measurements.
3. Use subdirectories for images (`data/grandma/` does not exist).
4. Modify or remove theological elements.
5. "Fix" grandma's spelling, grammar, or wording.
6. Guess what unclear handwriting says.
7. Read images without checking dimensions first.
8. Skip validation after making changes.
9. Read more than **100** images at once — API limit.

## Do

1. Run `python scripts/image_safeguards.py status` before reading images.
2. Use `[UNCLEAR]` for unreadable text.
3. Preserve original recipe notes verbatim.
4. Check dimensions before processing (2000 px limit).
5. Run `python scripts/validate-recipes.py` after changes.
6. Use `data/processed/` images for AI reading.
7. Keep image paths flat: `data/filename.jpeg`.
8. Match collection ID format: `grandma-baker` (not `grandma`).
9. Commit and push all changes before ending a session.
10. Document WIP in `.claude/*.md` files for session continuity.

## Common Errors

### Image path

```
WRONG:  data/grandma/image.jpeg   (subdirectory doesn't exist)
RIGHT:  data/image.jpeg            (flat structure)
```

### Collection ID mismatch

```
WRONG:  collection: "grandma"        (old format)
RIGHT:  collection: "grandma-baker"  (current)
```

### Image size

```
WRONG:  data/Grandmas-recipes - 12.jpeg   (may be 4032×3024)
RIGHT:  data/processed/Grandmas-recipes - 12.jpeg   (≤2000 px)
```

### Image count (API limit)

```
ERROR:  "Too much media: 0 document pages + 103 images > 100"
CAUSE:  API limit is 100 images per request
FIX:    Process in batches ≤ 100
```
