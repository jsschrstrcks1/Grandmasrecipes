# Recipe Validation Skill

**Purpose:** Ensure all recipes conform to the schema and pass quality checks before being added to the archive.

**Activation:** This skill activates when editing `recipes_master.json`, or when keywords like "validate", "check", "schema", or "recipe errors" appear.

---

## Core Responsibilities

1. **Schema Compliance** — Ensure all required fields are present
2. **Data Quality** — Flag suspicious values (too much salt, impossible temperatures)
3. **Consistency** — Maintain uniform formatting across all recipes
4. **Image Integrity** — Verify referenced images exist

---

## Recipe Schema

### Required Fields

```json
{
  "id": "string (kebab-case slug)",
  "title": "string (exact title from source)",
  "category": "string (from valid list)",
  "ingredients": ["array of strings"],
  "instructions": ["array of strings"]
}
```

### Optional Fields

```json
{
  "collection": "grandma-baker",
  "collection_display": "Grandma Baker",
  "attribution": "string",
  "source_note": "string",
  "description": "string",
  "servings_yield": "string",
  "prep_time": "string",
  "cook_time": "string",
  "total_time": "string",
  "temperature": "string (e.g., '350°F (175°C)')",
  "pan_size": "string",
  "notes": ["array of strings"],
  "tags": ["array of strings"],
  "confidence": "high|medium|low",
  "image_refs": ["array of filenames"],
  "conversions": {},
  "nutrition": {}
}
```

### Valid Categories

```
appetizers, beverages, breads, breakfast, desserts
mains, salads, sides, soups, snacks
```

---

## Validation Checks

### 1. Required Field Check
Every recipe MUST have:
- `id` — Unique, kebab-case identifier
- `title` — Human-readable recipe name
- `category` — From the valid categories list
- `ingredients` — Non-empty array
- `instructions` — Non-empty array

### 2. ID Validation
- Must be unique across all recipes
- Must be kebab-case (lowercase, hyphens only)
- Should match title slugified

### 3. Measurement Sanity Checks

| Ingredient | Max Expected |
|------------|--------------|
| Salt | 0.5 cups, 3 tbsp, or 6 tsp |
| Sugar | 6 cups |
| Flour | 10 cups |
| Butter | 4 cups |
| Baking soda | 4 tsp |
| Baking powder | 4 tbsp |

### 4. Temperature Sanity
- Minimum: 200°F
- Maximum: 550°F
- Format: Should include both F and C when possible

### 5. Image Reference Check
- All files in `image_refs` should exist in `data/` directory
- Warn if image file not found

---

## Running Validation

```bash
# Full validation
python scripts/validate-recipes.py

# Strict mode (fail on warnings too)
python scripts/validate-recipes.py --strict
```

---

## Common Validation Errors

### Missing Required Field
```
ERROR [recipe-id]: Missing required field: ingredients
```
**Fix:** Add the missing field to the recipe.

### Invalid Category
```
ERROR [recipe-id]: Invalid category: 'desert' (valid: appetizers, beverages, ...)
```
**Fix:** Use correct spelling from valid categories list.

### Duplicate ID
```
ERROR [recipe-id]: Duplicate recipe ID
```
**Fix:** Make the ID unique by adding a suffix or clarifying name.

### Suspicious Measurement
```
WARNING [recipe-id]: Suspicious: 5 tbsp salt (max expected: 3 tbsp)
```
**Action:** Verify against source image — could be OCR error (`tbsp` vs `tsp`).

### Missing Image
```
WARNING [recipe-id]: Referenced image not found: filename.jpeg
```
**Action:** Verify image filename spelling, or remove reference if image doesn't exist.

---

## Post-Validation Actions

After validation passes:

1. **Commit changes** with descriptive message
2. **Reference the validation** in commit: "Validated with validate-recipes.py"
3. **Note any warnings** that were intentionally ignored

---

## Guardrails

### MUST DO:
- Run validation after ANY edit to `recipes_master.json`
- Fix all ERRORs before committing
- Investigate all WARNINGs (may indicate OCR errors)
- Preserve the `[UNCLEAR]` markers — don't remove them

### MUST NOT:
- Commit recipes with validation errors
- Ignore suspicious measurement warnings without checking source
- Remove `[UNCLEAR]` markers without verifying against image
- Auto-fix errors by inventing data

---

## Integration with Hooks

The `post-write-validate.sh` hook automatically runs validation after edits to recipe files. Errors will be displayed in the hook output.

---

## Resources

- [validate-recipes.py](../../scripts/validate-recipes.py)
- [Recipe Schema](../../CLAUDE.md#recipe-schema)
- [OCR Correction Standards](../../CLAUDE.md#ocr-correction-standards)

---

*"Accuracy is more important than speed. These recipes matter deeply to this family."*
