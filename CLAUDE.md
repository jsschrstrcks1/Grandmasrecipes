# Grandma's Kitchen - Family Recipe Archive

## Project Mission & Values

This is a labor of love being performed by a Reformed Baptist family. Our ethos is **Soli Deo Gloria** (Glory to God Alone).

**Accuracy is more important than speed.** These recipes matter deeply to this family.

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

## Non-Negotiable Rules

1. **NEVER delete handwritten images**
2. **NEVER invent ingredients, steps, or measurements**
3. If unreadable, mark as `[UNCLEAR]`
4. Image paths are FLAT in data/ - no subdirectories
5. Always check image dimensions before reading

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

---

*"She looketh well to the ways of her household, and eateth not the bread of idleness."*
— Proverbs 31:27
