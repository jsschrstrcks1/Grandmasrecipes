# Maintenance Guide

This document provides detailed workflows for routine maintenance tasks in the Grandma's Recipe Archive.

---

## Table of Contents

1. [Adding a New Recipe](#adding-a-new-recipe)
2. [Adding a New Image](#adding-a-new-image)
3. [Transcribing a Handwritten Recipe](#transcribing-a-handwritten-recipe)
4. [Updating an Existing Recipe](#updating-an-existing-recipe)
5. [Pre-Deployment Checklist](#pre-deployment-checklist)
6. [Fixing Validation Errors](#fixing-validation-errors)
7. [Cross-Repository Synchronization](#cross-repository-synchronization)
8. [Script Reference](#script-reference)

---

## Adding a New Recipe

### Prerequisites
- Recipe image in `data/` directory
- Processed version in `data/processed/` (≤2000px)

### Step-by-Step

```bash
# 1. Process the image first (creates AI-safe version)
python scripts/process_images.py

# 2. Verify image is ready
python scripts/image_safeguards.py status
```

### 3. Transcribe the Recipe

Read the processed image and create the recipe JSON:

```json
{
  "id": "recipe-name-slug",
  "collection": "grandma-baker",
  "collection_display": "Grandma Baker",
  "title": "Recipe Title (exact from card)",
  "category": "desserts",
  "image_refs": ["Grandmas-recipes - XX.jpeg"],
  "ingredients": [
    "2 cups flour",
    "1 tsp salt"
  ],
  "instructions": [
    "Preheat oven to 350°F (175°C)",
    "Mix dry ingredients"
  ],
  "notes": [],
  "confidence": "high"
}
```

### 4. Add to recipes_master.json

Add the recipe to `data/recipes_master.json` in the appropriate location.

### 5. Validate and Rebuild

```bash
# Validate the recipe
python scripts/validate-recipes.py

# Rebuild ingredient index
python scripts/build-ingredient-index.py

# Rebuild search index (if using Pagefind)
python scripts/build-pagefind.py
```

### Checklist

- [ ] Image placed in `data/` (flat, no subdirectories)
- [ ] Image processed to ≤2000px
- [ ] Recipe JSON has all required fields (id, title, category, ingredients, instructions)
- [ ] Collection set to `grandma-baker`
- [ ] Category is valid (appetizers, beverages, breads, breakfast, desserts, mains, salads, sides, soups, snacks)
- [ ] Image reference matches actual filename
- [ ] Validation passes with no errors
- [ ] Ingredient index rebuilt

---

## Adding a New Image

### For Recipe Cards

```bash
# 1. Place original image in data/ directory
# Naming convention: Grandmas-recipes - XXX.jpeg

# 2. Process for AI reading
python scripts/process_images.py

# 3. Verify status
python scripts/image_safeguards.py status
```

### Image Requirements

| Requirement | Value |
|-------------|-------|
| Format | JPEG preferred |
| Max dimensions for AI | 2000px (either dimension) |
| Original storage | `data/` directory |
| Processed storage | `data/processed/` directory |
| Naming | `Grandmas-recipes - XXX.jpeg` |

### CRITICAL: Never Delete Handwritten Images

Handwritten recipe cards are **irreplaceable family heirlooms**. Only typed/printed recipes or magazine clippings may be deleted after ingestion.

---

## Transcribing a Handwritten Recipe

### Pre-Transcription

```bash
# Check image dimensions
python scripts/image_safeguards.py status

# Use processed version for reading
# ALWAYS: data/processed/filename.jpeg
# NEVER: data/filename.jpeg (may be oversized)
```

### OCR Guidelines

#### Common Misreadings to Watch For

| Misread | Correct | Context |
|---------|---------|---------|
| `l` | `1` | Numbers: `l cup` → `1 cup` |
| `1` | `l` | Words: `mi1k` → `milk` |
| `O` | `0` | Numbers: `35O°F` → `350°F` |
| `0` | `O` | Words: `0ven` → `Oven` |

#### Critical Measurement Checks

| If You Read | Double-Check | Why |
|-------------|--------------|-----|
| `tbsp` | Could be `tsp`? | 3x difference! |
| `tsp` | Could be `tbsp`? | 3x difference! |
| `1/4` | Could be `1/2`? | 2x difference |

#### When Uncertain

```json
"ingredients": [
  "1 cup flour",
  "[UNCLEAR] sugar",
  "[UNCLEAR: possibly '1/2' or '1/4'] cup milk"
]
```

### Confidence Ratings

| Rating | Criteria |
|--------|----------|
| `high` | All text clearly readable |
| `medium` | 1-3 unclear words marked with `[UNCLEAR]` |
| `low` | Significant portions unclear |

### Post-Transcription

```bash
# Always validate after adding
python scripts/validate-recipes.py
```

---

## Updating an Existing Recipe

### Finding a Recipe

Recipes are stored in `data/recipes_master.json`. Search by:
- Recipe ID (slug)
- Recipe title
- Category

### Making Changes

1. Locate recipe in `recipes_master.json`
2. Make edits (preserve original formatting/wording)
3. Update `notes` field if adding clarifications
4. Run validation

### Validation After Updates

```bash
python scripts/validate-recipes.py
```

### What NOT to Change

- Grandma's original spelling
- Grandma's grammar or phrasing
- `[UNCLEAR]` markers without verifying source image
- Theological elements or notes

---

## Pre-Deployment Checklist

Run these commands before deploying to GitHub Pages:

```bash
# 1. Validate all recipes (REQUIRED)
python scripts/validate-recipes.py

# 2. Rebuild ingredient index (REQUIRED)
python scripts/build-ingredient-index.py

# 3. Rebuild search index (REQUIRED if using Pagefind)
python scripts/build-pagefind.py

# 4. Process any new images (if added)
python scripts/process_images.py

# 5. Optimize images for production (optional)
python scripts/optimize_images.py

# 6. Minify assets (optional)
python scripts/minify.py
```

### Deployment Checklist

- [ ] All validation errors fixed
- [ ] No `[UNCLEAR]` markers that should be resolved
- [ ] Ingredient index up to date
- [ ] Search index rebuilt
- [ ] All new images processed
- [ ] Changes committed
- [ ] Changes pushed to GitHub

---

## Fixing Validation Errors

### Common Errors

#### Missing Required Field
```
ERROR [recipe-id]: Missing required field: ingredients
```
**Fix:** Add the missing field (ingredients, instructions, category, title, or id).

#### Invalid Category
```
ERROR [recipe-id]: Invalid category: 'desert'
```
**Fix:** Use correct category from: `appetizers, beverages, breads, breakfast, desserts, mains, salads, sides, soups, snacks`

#### Duplicate ID
```
ERROR [recipe-id]: Duplicate recipe ID
```
**Fix:** Add a suffix to make unique: `recipe-id-variation`, `recipe-id-2`

#### Suspicious Measurement
```
WARNING [recipe-id]: Suspicious: 5 tbsp salt
```
**Action:** Check source image — likely OCR error (`tbsp` vs `tsp`).

#### Missing Image
```
WARNING [recipe-id]: Referenced image not found
```
**Fix:** Check filename spelling or remove reference if image doesn't exist.

### Running Validation

```bash
# Standard validation
python scripts/validate-recipes.py

# Strict mode (fail on warnings too)
python scripts/validate-recipes.py --strict
```

---

## Cross-Repository Synchronization

### Family Repositories

| Collection | GitHub Repo | Collection ID |
|------------|-------------|---------------|
| Grandma Baker | [Grandmasrecipes](https://github.com/jsschrstrcks1/Grandmasrecipes) | `grandma-baker` |
| MomMom Baker | [MomsRecipes](https://github.com/jsschrstrcks1/MomsRecipes) | `mommom-baker` |
| Granny Hudson | [Grannysrecipes](https://github.com/jsschrstrcks1/Grannysrecipes) | `granny-hudson` |
| Other Recipes | [Allrecipes](https://github.com/jsschrstrcks1/Allrecipes) | `all` |

### Syncing Standards

When updating shared standards, sync across all repositories:

1. Update `CROSS_REPO_STANDARDS.md` in hub repo (Grandmasrecipes)
2. Create matching updates in each family repo
3. Ensure schema compatibility

### What to Sync

- Recipe schema (required fields)
- Valid categories list
- Measurement abbreviations
- `[UNCLEAR]` marker format
- Confidence ratings

### What NOT to Sync

- Collection IDs (repo-specific)
- Image path prefixes (repo-specific)
- Repository-specific notes

---

## Script Reference

### validate-recipes.py

**Purpose:** Validate all recipes in `recipes_master.json`

```bash
python scripts/validate-recipes.py           # Standard validation
python scripts/validate-recipes.py --strict  # Fail on warnings
```

**Checks:**
- Required fields present
- Valid category
- Unique recipe IDs
- Measurement sanity
- Image references exist

---

### process_images.py

**Purpose:** Create AI-safe versions of images (≤2000px)

```bash
python scripts/process_images.py                    # Process all
python scripts/process_images.py --collection grandma  # Specific collection
```

**Output:** Creates resized images in `data/processed/`

---

### image_safeguards.py

**Purpose:** Check image status and dimensions

```bash
python scripts/image_safeguards.py status     # Show all image statuses
python scripts/image_safeguards.py validate   # Validate all images
python scripts/image_safeguards.py next       # Get next processable image
```

---

### build-ingredient-index.py

**Purpose:** Build searchable ingredient index

```bash
python scripts/build-ingredient-index.py
```

**Output:** Updates ingredient search data

---

### build-pagefind.py

**Purpose:** Build Pagefind search index

```bash
python scripts/build-pagefind.py
```

**Output:** Creates search index for the site

---

### optimize_images.py

**Purpose:** Optimize images for production (compression, WebP)

```bash
python scripts/optimize_images.py
```

---

### minify.py

**Purpose:** Minify CSS/JS assets

```bash
python scripts/minify.py
```

---

## Quick Reference

### Most Common Tasks

| Task | Command |
|------|---------|
| Validate recipes | `python scripts/validate-recipes.py` |
| Process new images | `python scripts/process_images.py` |
| Check image status | `python scripts/image_safeguards.py status` |
| Rebuild ingredient index | `python scripts/build-ingredient-index.py` |
| Rebuild search | `python scripts/build-pagefind.py` |

### After Adding Recipe

```bash
python scripts/validate-recipes.py
python scripts/build-ingredient-index.py
```

### After Adding Image

```bash
python scripts/process_images.py
python scripts/image_safeguards.py status
```

### Before Deploy

```bash
python scripts/validate-recipes.py
python scripts/build-ingredient-index.py
python scripts/build-pagefind.py
```

---

*Last updated: 2026-01*
