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
8. [Hub Aggregation Workflow](#hub-aggregation-workflow)
9. [Script Reference](#script-reference)

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

## Hub Aggregation Workflow

Grandmasrecipes serves as the **hub** that aggregates recipes from all family collections into a single searchable archive.

### Overview

The aggregation script fetches recipes from remote family repositories and merges them with local recipes into `recipes_master.json`. This enables the hub to display all family recipes (~5,000+) in one place.

### Remote Collections

| Collection | Source URL | Collection ID |
|------------|------------|---------------|
| MomMom Baker | `https://jsschrstrcks1.github.io/MomsRecipes/data/recipes.json` | `mommom-baker` |
| Granny Hudson | `https://jsschrstrcks1.github.io/Grannysrecipes/granny/recipes_master.json` | `granny-hudson` |
| Other Recipes | `https://jsschrstrcks1.github.io/Allrecipes/data/recipes.json` | `all` |

### Running Aggregation

```bash
# Standard aggregation (fetches and merges all remote collections)
python scripts/aggregate_collections.py

# Dry run (shows what would be fetched without modifying files)
python scripts/aggregate_collections.py --dry-run

# Local only (skip remote fetch, just normalize existing recipes)
python scripts/aggregate_collections.py --local-only
```

### What the Script Does

1. **Loads local recipes** from `data/recipes_master.json`
2. **Fetches remote recipes** from each family repository's GitHub Pages
3. **Normalizes collection IDs** (e.g., `mommom` → `mommom-baker`, `reference` → `all`)
4. **Resolves image paths** for remote collections (converts relative to absolute URLs)
5. **Merges recipes** without duplicates (uses recipe ID + collection as key)
6. **Updates meta counts** for accurate facet display
7. **Saves merged results** back to `recipes_master.json`

### Image Path Resolution

For remote collections, the script converts relative image paths to absolute URLs:

```
# Before (relative)
"image_refs": ["Moms Recipes - 42.jpeg"]

# After (absolute URL)
"image_refs": ["https://jsschrstrcks1.github.io/MomsRecipes/data/Moms Recipes - 42.jpeg"]
```

This ensures images display correctly when viewing recipes from remote collections in the hub.

### After Aggregation

After running the aggregation script, complete these steps:

```bash
# 1. Validate all merged recipes
python scripts/validate-recipes.py

# 2. Rebuild ingredient index with all recipes
python scripts/build-ingredient-index.py

# 3. Rebuild search index (if using Pagefind)
python scripts/build-pagefind.py
```

### When to Run Aggregation

| Scenario | Run Aggregation? |
|----------|------------------|
| Before major deployment | Yes |
| After adding recipes to remote repos | Yes |
| Weekly/monthly maintenance | Recommended |
| Only local changes to Grandma Baker | Not required |

### Troubleshooting

#### Remote Collection Returns 404

```
WARNING: Could not fetch granny-hudson: 404 Client Error
```

**Cause:** The remote repository may not have published `data/recipes.json` yet.

**Action:** Check that the remote repo has:
1. A `data/recipes.json` file
2. GitHub Pages enabled and deployed

#### Collection ID Mismatch in UI

If facet counts show 0 for a collection:

1. Check `script.js` has the collection ID in the `counts` object
2. Check `index.html` has a checkbox with matching `data-collection` attribute
3. Verify recipes have the correct `collection` field value

### Aggregation Checklist

- [ ] Run `python scripts/aggregate_collections.py`
- [ ] Run `python scripts/aggregate_tips.py`
- [ ] Verify expected recipe counts (check script output)
- [ ] Run validation: `python scripts/validate-recipes.py`
- [ ] Rebuild ingredient index: `python scripts/build-ingredient-index.py`
- [ ] Test locally: open `index.html` and check facet counts
- [ ] Commit and push changes

---

## Tips Aggregation

Kitchen tips are also aggregated from family repositories to display relevant wisdom when viewing recipes.

### Remote Tips Sources

| Collection | Source URL | Tips Count |
|------------|------------|------------|
| MomMom Baker | `data/tips.json` | ~113 |
| Other Recipes | `data/tips_master.json` | ~27 |
| Granny Hudson | (embedded in recipe notes) | — |

### Running Tips Aggregation

```bash
python scripts/aggregate_tips.py           # Full aggregation
python scripts/aggregate_tips.py --dry-run # Preview without saving
```

### Tips Format

Tips are organized by category in `data/kitchen-tips.json`:

```json
{
  "categories": [
    {
      "id": "baking-general",
      "name": "Baking Tips",
      "icon": "🧁",
      "tips": [
        {
          "text": "For high altitude baking...",
          "attribution": "MomMom Baker",
          "collection": "mommom-baker"
        }
      ]
    }
  ]
}
```

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

### aggregate_collections.py

**Purpose:** Fetch and merge recipes from all family repositories

```bash
python scripts/aggregate_collections.py            # Full aggregation
python scripts/aggregate_collections.py --dry-run  # Preview without saving
python scripts/aggregate_collections.py --local-only  # Skip remote fetch
```

**Actions:**
- Fetches recipes from MomsRecipes, Grannysrecipes, Allrecipes
- Normalizes collection IDs to standard format
- Resolves image paths to absolute URLs for remote collections
- Merges without duplicates
- Updates meta counts

**Output:** Updates `data/recipes_master.json` with all aggregated recipes

---

### aggregate_tips.py

**Purpose:** Fetch and merge kitchen tips from family repositories

```bash
python scripts/aggregate_tips.py            # Full aggregation
python scripts/aggregate_tips.py --dry-run  # Preview without saving
```

**Sources:**
- MomsRecipes: `data/tips.json` (~113 tips)
- Allrecipes: `data/tips_master.json` (~27 tips)
- Local: `data/kitchen-tips.json` (~54 tips)

**Output:** Updates `data/kitchen-tips.json` with merged tips organized by category

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
| Aggregate recipes | `python scripts/aggregate_collections.py` |
| Aggregate tips | `python scripts/aggregate_tips.py` |

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

### Before Deploy (Hub with All Collections)

```bash
python scripts/aggregate_collections.py   # Fetch all family recipes
python scripts/aggregate_tips.py          # Fetch all family tips
python scripts/validate-recipes.py        # Validate merged recipes
python scripts/build-ingredient-index.py  # Rebuild ingredient index
python scripts/build-pagefind.py          # Rebuild search index
```

---

*Last updated: 2026-01*
