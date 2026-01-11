# Cross-Repository Standards

This document defines standards that should be synchronized across all family recipe repositories.

---

## Family Recipe Repositories

| Repository | Collection ID | Owner | Purpose |
|------------|---------------|-------|---------|
| Grandmasrecipes | `grandma-baker` | Grandma Baker | Primary archive + hub |
| MomsRecipes | `mommom-baker` | MomMom Baker | MomMom's collection |
| Grannysrecipes | `granny-hudson` | Granny Hudson | Granny's collection |
| Allrecipes | `all` | Reference | Magazine clippings, misc |

---

## Shared Standards

### 1. Recipe Schema (Must Match)

All repositories should use the same recipe schema:

```json
{
  "id": "recipe-slug",
  "collection": "collection-id",
  "collection_display": "Display Name",
  "title": "Recipe Title",
  "category": "category",
  "ingredients": [],
  "instructions": [],
  "notes": [],
  "image_refs": [],
  "confidence": "high|medium|low"
}
```

### 2. Valid Categories (Must Match)

All repositories must use these exact categories:

```
appetizers, beverages, breads, breakfast, desserts
mains, salads, sides, soups, snacks
```

### 3. Measurement Abbreviations (Must Match)

| Type | Abbreviations |
|------|---------------|
| Volume | tsp, tbsp, cup, fl oz, pt, qt, gal |
| Weight | oz, lb |
| Temperature | Dual format: `350°F (175°C)` |

### 4. Confidence Ratings (Must Match)

| Rating | Meaning |
|--------|---------|
| `high` | All text clearly readable |
| `medium` | 1-3 unclear words |
| `low` | Significant portions unclear |

### 5. Unclear Text Marker (Must Match)

Always use: `[UNCLEAR]` or `[UNCLEAR: possible readings]`

---

## Repository-Specific Settings

### Collection IDs

Each repo must use its designated collection ID:

| Repo | Collection ID | Display Name |
|------|---------------|--------------|
| Grandmasrecipes | `grandma-baker` | Grandma Baker |
| MomsRecipes | `mommom-baker` | MomMom Baker |
| Grannysrecipes | `granny-hudson` | Granny Hudson |
| Allrecipes | `all` | Other Recipes |

### Image Paths

Each repo has its own image structure:

| Repo | Image Path | Prefix |
|------|------------|--------|
| Grandmasrecipes | `data/` | `Grandmas-recipes` |
| MomsRecipes | `data/` | `Moms Recipes` |
| Grannysrecipes | `data/` | `Granny` |
| Allrecipes | `data/` | Various |

---

## Synchronization Checklist

When updating standards, sync these files across all repos:

### Must Sync:
- [ ] Recipe schema definition
- [ ] Valid categories list
- [ ] Measurement abbreviations
- [ ] Confidence ratings
- [ ] `[UNCLEAR]` marker format

### Repo-Specific (Don't Sync):
- Collection ID
- Image path prefixes
- Repository-specific notes

---

## Hub Aggregation

Grandmasrecipes serves as the hub, aggregating from all collections:

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

### Image URL Resolution

When displaying recipes from remote collections, image paths must be resolved:

```javascript
// Local collection
image_path = `data/${image_ref}`

// Remote collection
image_path = `https://jsschrstrcks1.github.io/${repo}/data/${image_ref}`
```

---

## Validation Scripts

All repos should use compatible validation scripts:

### Required Checks:
1. Required fields present
2. Valid category
3. Unique recipe ID
4. Measurement sanity checks
5. Image reference verification

### Shared Sanity Limits:

```python
SANITY_LIMITS = {
    'salt': {'max_cups': 0.5, 'max_tbsp': 3, 'max_tsp': 6},
    'sugar': {'max_cups': 6},
    'flour': {'max_cups': 10},
    'butter': {'max_cups': 4},
    'baking soda': {'max_tsp': 4},
    'baking powder': {'max_tbsp': 4},
}

TEMP_MIN = 200  # Fahrenheit
TEMP_MAX = 550  # Fahrenheit
```

---

## CLAUDE.md Standards

All repos should include in their CLAUDE.md:

### Required Sections:
1. Quick Start (30-second version)
2. Priority Framework
3. Recipe Schema
4. Valid Categories
5. OCR Correction Standards
6. Non-Negotiable Rules
7. Guardrails (Accept/Reject)
8. Do's and Don'ts

### Required Principles:
- **Accuracy > Speed**
- **Never delete handwritten images**
- **Never invent data**
- **Use `[UNCLEAR]` for uncertain text**
- **Soli Deo Gloria**

---

## Version Alignment

When major changes are made to shared standards:

1. Update this document first
2. Create PR in each repository
3. Reference this document in PR description
4. Ensure all repos update to same version

### Current Versions:

| Standard | Version | Last Updated |
|----------|---------|--------------|
| Recipe Schema | 1.0 | 2026-01 |
| Categories | 1.0 | 2026-01 |
| OCR Standards | 1.0 | 2026-01 |
| Validation Rules | 1.0 | 2026-01 |

---

## Theological Foundation

All repositories share the same foundation:

> **Soli Deo Gloria** — Glory to God Alone
>
> *"She looketh well to the ways of her household, and eateth not the bread of idleness."*
> — Proverbs 31:27

This is a labor of love by a Reformed Baptist family. These recipes are irreplaceable family heirlooms.

---

## Contact for Standards Questions

For questions about cross-repo standards or synchronization, check:
1. This document first
2. The hub repository (Grandmasrecipes) CLAUDE.md
3. The specific repository's CLAUDE.md

---

*Last updated: 2026-01*
