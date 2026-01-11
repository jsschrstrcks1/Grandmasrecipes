# Grandma's Kitchen - Family Recipe Archive

## Project Mission & Values

This is a labor of love being performed by a Reformed Baptist family. Our ethos is **Soli Deo Gloria** (Glory to God Alone).

**Accuracy is more important than speed.** These recipes matter deeply to this family.

---

## Quick Start (30-Second Version)

1. **Images are FLAT** in `data/` — no subdirectories exist
2. **NEVER delete handwritten images** — irreplaceable family heirlooms
3. **NEVER invent** ingredients, steps, or measurements
4. **Mark unclear text** as `[UNCLEAR]` — don't guess
5. **Accuracy > Speed** — these recipes matter deeply
6. **Run validation** after changes: `python scripts/validate-recipes.py`

---

## Priority Framework (Decision-Making)

When making decisions, follow this priority order:

| Priority | Principle | Explanation |
|----------|-----------|-------------|
| 1 | **Accuracy-First** | Never guess or invent recipe content |
| 2 | **Preservation-First** | Handwritten images are sacred heirlooms |
| 3 | **Fidelity-First** | Preserve grandma's exact wording |
| 4 | **Readability-First** | Family members need clear, usable recipes |

---

## Repository Purpose

This repository serves TWO functions:

### 1. Collection: Grandma Baker's Recipes
Contains Grandma Baker's personal recipe collection - handwritten cards, family favorites from Michigan to Florida.

### 2. Hub: Family Recipe Archive
The central site that can aggregate recipes from all family collections:
- **Grandma Baker** (this repo - local)
- **MomMom Baker** (MomsRecipes repo - remote)
- **Granny Hudson** (Grannysrecipes repo - remote)
- **Other Family Recipes** (Allrecipes repo - remote)

---

## Repository Structure

```
Grandmasrecipes/
├── index.html              # Main page (hub + local recipes)
├── recipe.html             # Recipe detail page
├── styles.css              # Stylesheet
├── script.js               # Client-side rendering + aggregation
├── CLAUDE.md               # THIS FILE - AI assistant instructions
├── README.md               # Project documentation
├── .claude/
│   ├── settings.json       # Claude Code configuration + hooks
│   ├── skill-rules.json    # Skill auto-activation rules
│   ├── mcp-servers.md      # MCP server documentation
│   ├── CROSS_REPO_STANDARDS.md  # Cross-repository sync standards
│   ├── MAINTENANCE.md      # Detailed maintenance workflows
│   ├── hooks/
│   │   ├── post-write-validate.sh  # Auto-validate after edits
│   │   └── image-safety-check.sh   # Warn about oversized images
│   └── skills/
│       ├── recipe-transcription/   # OCR + transcription skill
│       │   └── SKILL.md
│       └── recipe-validation/      # Schema validation skill
│           └── SKILL.md
├── data/
│   ├── recipes_master.json # Grandma Baker's recipes (LOCAL)
│   ├── collections.json    # Hub configuration
│   ├── *.jpeg              # Recipe images (FLAT - no subdirectories!)
│   └── processed/          # AI-safe resized images (≤2000px)
├── scripts/
│   ├── validate-recipes.py
│   ├── process_images.py
│   └── image_safeguards.py
└── ebook/
    └── (print generation files)
```

### CRITICAL: Image Path Structure

**Images are FLAT in data/ directory. There are NO subdirectories.**

```
CORRECT: data/Grandmas-recipes - 12.jpeg
WRONG:   data/grandma/Grandmas-recipes - 12.jpeg  ← subdirectory doesn't exist!
```

The `getCollectionImagePath()` function in script.js should return `'data/'` for local images.

---

## Image Handling

### HANDWRITTEN IMAGES ARE SACRED

Grandma Baker's handwritten recipe cards are **irreplaceable family heirlooms**.

| Image Type | Action |
|------------|--------|
| Handwritten recipe cards | **NEVER DELETE** - preserve, optimize, display |
| Typed/printed recipes | May delete after JSON ingestion |
| Magazine clippings | May delete after JSON ingestion |

### Oversized Images

Many images exceed Claude's 2000px API limit:
- Original iPhone photos: up to 4032x3024px
- Always use `data/processed/*.jpeg` for AI reading
- Run `python scripts/process_images.py` to create safe versions

### Before Reading ANY Image

```bash
python scripts/image_safeguards.py status
```

---

## Hub Aggregation (Future/Optional)

The hub can fetch recipes from other family repos:

```javascript
const FAMILY_COLLECTIONS = [
  { id: 'grandma-baker', name: "Grandma Baker", local: true },
  { id: 'mommom-baker', name: "MomMom Baker",
    url: 'https://jsschrstrcks1.github.io/MomsRecipes/data/recipes.json' },
  { id: 'granny-hudson', name: "Granny Hudson",
    url: 'https://jsschrstrcks1.github.io/Grannysrecipes/data/recipes.json' },
  { id: 'all', name: "Other Recipes",
    url: 'https://jsschrstrcks1.github.io/Allrecipes/data/recipes.json' }
];
```

When aggregating, image paths must be resolved to absolute URLs for remote collections.

---

## Family Repositories

| Collection | GitHub Repo | GitHub Pages | Collection ID |
|------------|-------------|--------------|---------------|
| Grandma Baker | [Grandmasrecipes](https://github.com/jsschrstrcks1/Grandmasrecipes) | [Live Site](https://jsschrstrcks1.github.io/Grandmasrecipes/) | `grandma-baker` |
| MomMom Baker | [MomsRecipes](https://github.com/jsschrstrcks1/MomsRecipes) | [Live Site](https://jsschrstrcks1.github.io/MomsRecipes/) | `mommom-baker` |
| Granny Hudson | [Grannysrecipes](https://github.com/jsschrstrcks1/Grannysrecipes) | [Live Site](https://jsschrstrcks1.github.io/Grannysrecipes/) | `granny-hudson` |
| Other Recipes | [Allrecipes](https://github.com/jsschrstrcks1/Allrecipes) | [Live Site](https://jsschrstrcks1.github.io/Allrecipes/) | `all` |

---

## Routine Maintenance

For detailed workflows, see [.claude/MAINTENANCE.md](.claude/MAINTENANCE.md).

### Adding a New Recipe

1. Add image to `data/` (flat, no subdirectories)
2. Process image: `python scripts/process_images.py`
3. Transcribe using processed image in `data/processed/`
4. Add recipe JSON to `data/recipes_master.json`
5. Validate: `python scripts/validate-recipes.py`
6. Rebuild indexes: `python scripts/build-ingredient-index.py`

### Adding a New Image

1. Place image in `data/` directory
2. Run: `python scripts/process_images.py`
3. Verify with: `python scripts/image_safeguards.py status`

### Before Deployment

```bash
python scripts/validate-recipes.py      # Validate all recipes
python scripts/build-ingredient-index.py # Rebuild ingredient index
python scripts/build-pagefind.py         # Rebuild search index
python scripts/minify.py                 # Minify assets (optional)
```

---

## Recipe Schema

```json
{
  "id": "recipe-slug",
  "collection": "grandma-baker",
  "collection_display": "Grandma Baker",
  "title": "Recipe Name",
  "category": "desserts",
  "image_refs": ["Grandmas-recipes - 12.jpeg"],
  "ingredients": [...],
  "instructions": [...],
  "notes": []
}
```

### Categories

```
appetizers, beverages, breads, breakfast, desserts
mains, salads, sides, soups, snacks
```

---

## Validation

```bash
python scripts/validate-recipes.py
```

---

## OCR Correction Standards

When transcribing handwritten recipe cards, watch for these common misreadings:

### Character Confusion
| Misread | Correct | Context |
|---------|---------|---------|
| `l` | `1` | Numbers (e.g., `l cup` → `1 cup`) |
| `1` | `l` | Words (e.g., `mi1k` → `milk`) |
| `O` | `0` | Numbers (e.g., `35O°F` → `350°F`) |
| `0` | `O` | Words (e.g., `0ven` → `Oven`) |

### Critical Measurement Distinctions
| DANGEROUS | CORRECT | Impact |
|-----------|---------|--------|
| `tbsp` | `tsp` | 3x difference! |
| `tsp` | `tbsp` | 3x difference! |
| `cup` | `cups` | Quantity matters |
| `oz` | `fl oz` | Weight vs volume |

### Measurement Standardization
Use these abbreviations consistently:
- **Volume:** tsp, tbsp, cup, fl oz, pt, qt, gal
- **Weight:** oz, lb
- **Temperature:** Dual format `350°F (175°C)`

### When Uncertain
- Mark with `[UNCLEAR]` — never guess
- Note possible readings: `[UNCLEAR: possibly "1/2" or "1/4"]`
- Flag for human review in recipe notes

---

## Non-Negotiable Rules

1. **NEVER delete handwritten images**
2. **NEVER invent ingredients, steps, or measurements**
3. If unreadable, mark as `[UNCLEAR]`
4. Image paths are FLAT in data/ - no subdirectories
5. Always check image dimensions before reading

---

## Guardrails: Accept vs Reject

| ✅ ACCEPT | ❌ REJECT |
|-----------|-----------|
| Verbatim transcription from source | Inventing missing ingredients or steps |
| `[UNCLEAR]` for unreadable text | Guessing measurements or quantities |
| Preserving grandma's exact wording | "Improving" or modernizing her text |
| Notes about image quality issues | Deleting ANY handwritten images |
| Marking uncertain readings | Assuming what a smudged word says |
| Original spelling and grammar | "Correcting" her personal style |
| Flat image paths in `data/` | Creating subdirectories for images |

---

## Do's and Don'ts

### ❌ Don't:
1. Delete handwritten images — **EVER** (they are irreplaceable)
2. Invent ingredients, steps, or measurements
3. Use subdirectories for images (`data/grandma/` doesn't exist)
4. Modify or remove theological elements
5. "Fix" grandma's spelling, grammar, or wording
6. Guess what unclear handwriting says
7. Read images without checking dimensions first
8. Skip validation after making changes

### ✅ Do:
1. Run `python scripts/image_safeguards.py status` before reading images
2. Use `[UNCLEAR]` for any unreadable text
3. Preserve original recipe notes verbatim
4. Check image dimensions before processing (2000px limit)
5. Run `python scripts/validate-recipes.py` after changes
6. Use `data/processed/` images for AI reading
7. Keep image paths flat: `data/filename.jpeg`
8. Match collection ID format: `grandma-baker` (not `grandma`)

---

## Common Errors to Avoid

### Image Path Error
```
WRONG: data/grandma/image.jpeg  (subdirectory doesn't exist)
RIGHT: data/image.jpeg          (flat structure)
```

### Collection ID Mismatch
```
WRONG: collection: "grandma"        (old format)
RIGHT: collection: "grandma-baker"  (current format)
```

### Image Size Error
```
WRONG: Reading data/Grandmas-recipes - 12.jpeg directly (may be 4032x3024)
RIGHT: Reading data/processed/Grandmas-recipes - 12.jpeg (≤2000px)
```

---

## Help & Support

| Question Type | Where to Look |
|---------------|---------------|
| Recipe JSON format | Check schema in `data/recipes_master.json` |
| Image safety | Run `python scripts/image_safeguards.py status` |
| Validation errors | Run `python scripts/validate-recipes.py` |
| Category options | See Categories section above |
| Hub/aggregation | See `data/collections.json` |
| Theological context | See Proverbs 31:27 citation below |

### Quick Reference Commands

```bash
# Check image status before reading
python scripts/image_safeguards.py status

# Validate all recipes after changes
python scripts/validate-recipes.py

# Process oversized images for AI reading
python scripts/process_images.py
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.4 | 2026-01 | Added Family Repositories table, Routine Maintenance section, MAINTENANCE.md |
| v1.3 | 2026-01 | Added skills (recipe-transcription, recipe-validation), skill-rules.json, MCP docs, cross-repo standards |
| v1.2 | 2026-01 | Added .claude/ hooks, OCR correction standards, measurement standardization |
| v1.1 | 2026-01 | Added Quick Start, Priority Framework, Guardrails, expanded Do's/Don'ts |
| v1.0 | — | Original CLAUDE.md structure |

---

*"She looketh well to the ways of her household, and eateth not the bread of idleness."*
— Proverbs 31:27
