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

## Processing Cookbook Collections

When processing scanned cookbook images (like church/community cookbooks), save **ALL** content.

### CRITICAL REQUIREMENTS

1. **ALL recipes** must be recorded in the JSON - no exceptions
2. **ALL handwritten images** must be saved and linked in recipe cards via `image_refs`
3. **ALL tips** must be saved as JSON entries
4. **If a tip page has handwriting**, save the image AND link it in the database

### What to Preserve

| Content Type | How to Save |
|--------------|-------------|
| **ALL Recipes** | Standard recipe JSON entries - EVERY recipe transcribed |
| **Household Hints/Tips** | Separate JSON entry with category "tips" |
| **Cooking Tips Pages** | Full transcription in dedicated entry |
| **Handwritten Tips** | Save image + link in `image_refs` + transcribe |
| **Inspirational Quotes** | Include in recipe notes when on same page |
| **Grandma's Handwritten Notes** | Always preserve - canonical precedence |
| **Front Cover Indexes** | Note which recipes were Grandma's favorites |
| **Publication Year** | Record in cookbook metadata |

### Grandma's Handwriting Has Precedence

When a recipe has both printed text AND Grandma's handwritten variations:
1. Save the **original printed recipe** first
2. Save **Grandma's variation** as a separate entry OR in notes
3. Mark handwritten variations clearly - they take precedence over printed text

### Cookbook Metadata to Track

For each cookbook scanned:
- Title and subtitle
- Publisher/organization (e.g., church name)
- Publication year
- Location (city, state)
- Grandma's favorites (noted in front cover indexes)

### Example: Household Hints Entry

```json
{
  "id": "household-hints-centennial-1986",
  "collection": "grandma-baker",
  "title": "Household Hints",
  "category": "tips",
  "source_cookbook": "Centennial Recipes 1886-1986, Calvary Lutheran Church",
  "ingredients": [],
  "instructions": [
    "To prevent milk from scorching when scalding, rinse the pan in water first",
    "Sugar in fried cakes should be added to the milk - prevents absorbing fat",
    "Add one drop of vanilla to chocolate just before serving for improved flavor"
  ],
  "notes": ["From Centennial Recipes cookbook, Elk Rapids MI"]
}
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

### generate_index.py

**Purpose:** Create lightweight recipe index for faster page load

```bash
python scripts/generate_index.py
```

**Output:** Creates `data/recipes_index.json` from `recipes_master.json`

**When to run:** After aggregating recipes or modifying `recipes_master.json`

---

### estimate_nutrition.py

**Purpose:** Estimate nutritional information for recipes

```bash
python scripts/estimate_nutrition.py                    # Estimate all recipes
python scripts/estimate_nutrition.py --dry-run          # Preview without saving
python scripts/estimate_nutrition.py --recipe-id ID     # Specific recipe
python scripts/estimate_nutrition.py --force            # Re-estimate all
python scripts/estimate_nutrition.py --collection ID    # Specific collection
```

**Output:** Adds/updates `nutrition` field in recipes

**When to run:** When adding nutrition data to recipes or after adding new recipes

---

### repair_ocr.py

**Purpose:** Find and repair common OCR errors in recipes

```bash
python scripts/repair_ocr.py                # Find OCR issues
python scripts/repair_ocr.py --fix          # Apply fixes
python scripts/repair_ocr.py --dry-run      # Preview fixes
```

**Output:** Updates recipes with corrected OCR text

**When to run:** Periodically to clean up transcription errors

---

### analyze_duplicates.py

**Purpose:** Analyze potential duplicate recipes across collections

```bash
python scripts/analyze_duplicates.py
```

**Output:** Creates `data/duplicate_analysis.json` with duplicate candidates

**When to run:** Before merging collections or cleaning up recipes

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

## Sharded Repository Support

The hub supports both monolithic (`recipes.json`) and sharded (`recipes-index.json` + `recipes-{category}.json`) repository formats. Sharding improves performance for large collections by allowing on-demand loading of category-specific recipe data.

### Repository Formats

| Format | Structure | Best For |
|--------|-----------|----------|
| **Monolithic** | Single `recipes.json` file | Small collections (<500 recipes) |
| **Sharded** | Index + category shards | Large collections (500+ recipes) |

### Sharded Structure

```
data/
├── recipes-index.json       # Minimal metadata for all recipes + shard manifest
├── recipes-appetizers.json  # Full recipe data for appetizers
├── recipes-beverages.json   # Full recipe data for beverages
├── recipes-breads.json      # Full recipe data for breads
├── recipes-breakfast.json   # Full recipe data for breakfast
├── recipes-desserts.json    # Full recipe data for desserts
├── recipes-mains.json       # Full recipe data for mains
├── recipes-salads.json      # Full recipe data for salads
├── recipes-sides.json       # Full recipe data for sides
├── recipes-soups.json       # Full recipe data for soups
└── recipes.json             # (Optional) Fallback monolithic file
```

### Index File Format (`recipes-index.json`)

```json
{
  "meta": {
    "sharded": true,
    "shard_strategy": "by_category"
  },
  "shards": [
    { "category": "desserts", "file": "recipes-desserts.json", "count": 150 },
    { "category": "mains", "file": "recipes-mains.json", "count": 200 }
  ],
  "recipes": [
    {
      "id": "recipe-slug",
      "title": "Recipe Name",
      "category": "desserts",
      "tags": ["tag1", "tag2"],
      "description": "Brief description...",
      "servings_yield": "12 servings",
      "total_time": "45 minutes"
    }
  ]
}
```

### How Aggregation Handles Sharded Repos

The `aggregate_collections.py` script automatically:

1. **Detects format**: Checks for `recipes-index.json` to determine if repo is sharded
2. **Fetches shards**: Downloads all category shards in parallel
3. **Falls back**: Uses monolithic `recipes.json` if shards fail
4. **Merges**: Combines all recipes into local `recipes_master.json`

```bash
# Aggregation output shows format detection:
python scripts/aggregate_collections.py -v

# Example output:
#   Other Recipes (all)...
#     Sharded format detected (11 category shards)
#       Fetching shard: recipes-desserts.json
#       OK: recipes-desserts.json (150 recipes)
#       ...
#     Fetched: 1500 recipes
```

### Client-Side Shard Loading

The `script.js` client also supports on-demand shard loading:

- **Automatic**: When viewing a recipe from a sharded collection, only that category's shard is loaded
- **Preload**: Use `preloadRemoteCollection('all')` in browser console to preload all shards
- **Cached**: Loaded shards are cached in memory for the session

### Converting a Repo to Sharded Format

To convert a family repository to sharded format:

```python
# scripts/create_shards.py (run in the target repo)
import json
from pathlib import Path

with open('data/recipes.json', 'r') as f:
    data = json.load(f)

recipes = data['recipes']
meta = data.get('meta', {})

# Group by category
by_category = {}
for r in recipes:
    cat = r.get('category', 'uncategorized')
    by_category.setdefault(cat, []).append(r)

# Create index with minimal metadata
index_recipes = [{
    'id': r.get('id'),
    'title': r.get('title'),
    'category': r.get('category'),
    'tags': r.get('tags', []),
    'collection': r.get('collection'),
    'description': (r.get('description', '') or '')[:100],
    'servings_yield': r.get('servings_yield', ''),
    'total_time': r.get('total_time', '') or r.get('cook_time', ''),
} for r in recipes]

# Build shard manifest
shards = [{'category': cat, 'file': f'recipes-{cat}.json', 'count': len(recs)}
          for cat, recs in sorted(by_category.items())]

# Write index
index_data = {
    'meta': {**meta, 'sharded': True, 'shard_strategy': 'by_category'},
    'shards': shards,
    'recipes': index_recipes
}
with open('data/recipes-index.json', 'w') as f:
    json.dump(index_data, f, indent=2)

# Write category shards
for cat, cat_recipes in by_category.items():
    shard_data = {
        'meta': {'category': cat, 'count': len(cat_recipes)},
        'recipes': cat_recipes
    }
    with open(f'data/recipes-{cat}.json', 'w') as f:
        json.dump(shard_data, f, indent=2)

print(f"Created {len(shards)} shards from {len(recipes)} recipes")
```

### Updating Collection Configuration

After a repo adopts sharding, update `REMOTE_COLLECTIONS` in:

1. **`scripts/aggregate_collections.py`**: Set `'sharded': True` and add `'index_url'`
2. **`script.js`**: Update the `REMOTE_COLLECTIONS` constant
3. **`data/collections.json`**: Update collection metadata

---

## Quick Reference

### Most Common Tasks

| Task | Command |
|------|---------|
| Validate recipes | `python scripts/validate-recipes.py` |
| Process new images | `python scripts/process_images.py` |
| Check image status | `python scripts/image_safeguards.py status` |
| Generate recipe index | `python scripts/generate_index.py` |
| Shard recipes | `python scripts/shard_recipes.py` |
| Rebuild ingredient index | `python scripts/build-ingredient-index.py` |
| Rebuild search | `python scripts/build-pagefind.py` |
| Aggregate recipes | `python scripts/aggregate_collections.py` |
| Aggregate tips | `python scripts/aggregate_tips.py` |
| Estimate nutrition | `python scripts/estimate_nutrition.py` |
| Find OCR errors | `python scripts/repair_ocr.py` |
| Find duplicates | `python scripts/analyze_duplicates.py` |
| Minify JS/CSS | `python scripts/minify.py` |

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
python scripts/shard_recipes.py           # Create category shards + lightweight index (CRITICAL!)
python scripts/build-ingredient-index.py  # Rebuild ingredient index
python scripts/build-pagefind.py          # Rebuild search index
python scripts/minify.py                  # Minify JS/CSS for production
```

---

## PWA Ingredient Search Maintenance

### Common Pantry Staples Exclusion

The PWA ingredient search excludes common pantry staples from the "Have:" and "Missing:" display to reduce noise. These are defined in `script.js` in the `COMMON_PANTRY_STAPLES` constant.

**Currently excluded:**
- Seasonings: salt, pepper, black pepper, white pepper, kosher salt, sea salt, garlic powder, onion powder, paprika, cayenne
- Liquids: water, oil, vegetable oil, cooking oil, canola oil, olive oil, cooking spray
- Baking: flour, all-purpose flour, sugar, granulated sugar, baking soda, baking powder, vanilla, vanilla extract
- Dairy: butter, unsalted butter, salted butter, margarine, eggs, egg, milk

**To add new exclusions:**
1. Edit `COMMON_PANTRY_STAPLES` Set in `script.js` (around line 87)
2. Add the ingredient in lowercase
3. Run `python scripts/minify.py`
4. Commit and push

### PWA Collection Filtering

The PWA search respects the collection filter checkboxes. If user selects only "Grandma", the ingredient search only returns Grandma's recipes.

### PWA and Recipe Grid Behavior

- When PWA search is active, the regular recipe grid is hidden
- When search is cleared, recipe grid reappears
- This is controlled in `updateIngredientSearchResults()` and `clearIngredientSearch()`

---

## Configuration Files

### data/collections.json

**Purpose:** Defines remote collection URLs and sharding configuration

**When to update:**
- Adding a new family repository
- Changing repository URLs
- Updating shard configuration

**Key fields:**
- `recipes_url` - URL to fetch recipes from
- `index_url` - URL to fetch lightweight index
- `sharded` - Whether collection uses category shards
- `recipe_count` - Approximate count (for display)

---

### data/substitutions.json

**Purpose:** Ingredient substitution rules for PWA search

**When to update:**
- Adding new ingredient substitutions
- Updating substitution ratios or notes

**Format:**
```json
{
  "id": "butter-margarine",
  "primary": "butter",
  "substitutes": [
    { "ingredient": "margarine", "ratio": "1:1", "notes": "..." }
  ]
}
```

---

### script.js Configuration Constants

Several constants in `script.js` may need periodic updates:

| Constant | Line | Purpose |
|----------|------|---------|
| `COMMON_PANTRY_STAPLES` | ~87 | Ingredients to exclude from PWA display |
| `CATEGORY_SHARDED_COLLECTIONS` | ~273 | Collections using category sub-shards |
| `currentFilter.collections` | ~147 | Default collection filter state |

After updating constants, run `python scripts/minify.py` and commit.

---

## Important Maintenance Reminder

**CRITICAL: Any time you add a feature that requires routine maintenance (rebuilding indexes, running scripts, updating configuration), ADD IT TO THIS FILE!**

Common maintenance triggers:
- Adding/modifying recipes → rebuild ingredient index, regenerate shards
- Adding/modifying images → process images
- Changing search behavior → rebuild Pagefind
- Changing ingredient handling → rebuild ingredient index
- Adding new collections → update aggregation config, collections.json
- Modifying PWA behavior → update script.js, run minify.py

---

*Last updated: 2026-01 (added missing scripts, configuration files, PWA maintenance)*
