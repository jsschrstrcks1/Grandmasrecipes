# Cross-Repository Duplicate Check Report

**Date:** 2026-01-29
**Session:** claude/review-repo-status-6VORt

---

## Summary

A comprehensive duplicate check was performed across all four recipe collections:

| Collection | Recipes | Description |
|------------|---------|-------------|
| grandma-baker | 937 | Local - Grandma Baker's handwritten collection |
| mommom-baker | 2,553 | Remote - MomMom Baker's recipes |
| granny-hudson | 184 | Remote - Granny Hudson's recipes |
| all | 5,722 | Remote - Digital cookbook collection |
| **Total** | **9,396** | |

---

## Findings

### Cross-Collection Duplicates: 314

These are recipes with the same normalized title appearing in **multiple collections**.

**Key Insight:** Most are **legitimate variants**, not true duplicates. The family collections appropriately preserve each grandmother's unique version of classic recipes.

Examples of legitimate variants:
- **Pumpkin Pie** (8 versions) - Dorothy Hardy's, honey version, Carnation's, various family sources
- **Rhubarb Pie** (7 versions) - Simple, Margaret Alland's, Foxfire, various sources
- **Carrot Cake** (6 versions) - Each collection has a family recipe
- **Key Lime Pie** (5 versions) - Tampa, Key West, baked, meringue versions

### Within-Collection Duplicates: 859

These are recipes with the same normalized title appearing **within a single collection**.

**Key Insight:** Most fall into these categories:

1. **Cheese aging variants (legitimate):** Parmigiano-Reggiano 12/18/24/30/36/40/48/60 month - intentionally different products
2. **Recipe variants (legitimate):** Small curd vs large curd cottage cheese, young vs aged versions
3. **Source variants (legitimate):** BHG (Better Homes & Gardens), FBC (Foxfire Book of Cooking), etc.
4. **Potential true duplicates (need review):** Some entries appear twice with only slight ID variations

---

## Potential True Duplicates (Needs Human Review)

These entries should be reviewed for consolidation:

### mommom-baker Collection

| Recipe | IDs | Action Suggested |
|--------|-----|------------------|
| Crepes | `crepes`, `crepes-bhg`, `crepes-egg-sausage-fbc-jasmine`, `crepes-fruit-fbc-jasmine` | Review if base crepe recipe is duplicated |
| Pan Gravy | `pan-gravy`, `pan-gravy-for-roasted-meat` (appears twice) | Likely true duplicate |
| Harvest Pot Roast | Appears twice | Likely true duplicate |
| Venison Pot Roast | Appears twice | Likely true duplicate |
| Beef Pot Roast | Appears twice | Likely true duplicate |

### granny-hudson Collection

| Recipe | IDs | Action Suggested |
|--------|-----|------------------|
| Quaker's Best Oatmeal Cookies | `quakers-best-oatmeal-cookies-granny`, `quaker-oatmeal-cookies-gr11-granny` | Likely true duplicate |
| Irish Soda Bread | `irish-soda-bread-granny`, `irish-soda-bread-landmark-tavern-granny` | Review - may be legitimate variants |

### all Collection

The "all" (Allrecipes/digital) collection has the most within-collection duplicates, primarily due to:
- Cheese aging levels (intentional and correct)
- Multiple source attributions for the same recipe
- French cheese name variations (e.g., `bleu-d-auvergne` vs `bleu-auvergne`)

---

## Recommendations

### No Action Required

1. **Cross-collection variants are acceptable** - Each family collection should preserve their grandmother's unique recipes
2. **Cheese aging variants are correct** - 12-month Parmigiano-Reggiano is a different product than 40-month
3. **Source-attributed variants are valuable** - BHG vs Foxfire versions may have meaningful differences

### Suggested Actions

1. **Review mommom-baker pot roast entries** - Harvest, Venison, and Beef pot roasts appear duplicated
2. **Review granny-hudson oatmeal cookies** - Appears to be same recipe with two IDs
3. **Consider adding "source" field** - To distinguish BHG vs Foxfire vs family versions without title confusion

---

## Script Location

A duplicate checking script was created at:
```
scripts/check-duplicates.py
```

Run with:
```bash
python scripts/check-duplicates.py
```

---

## Conclusion

**The duplicate check found no systemic problem.** The 314 cross-collection "duplicates" are almost entirely **legitimate family recipe variants** - different grandmothers' versions of classic recipes like pumpkin pie, carrot cake, and chocolate chip cookies.

The user's guidance that "variants are OK, exact duplicates are not" is being followed. A small number of true duplicates in mommom-baker (pot roast recipes) should be reviewed for consolidation.

---

*"She looketh well to the ways of her household, and eateth not the bread of idleness." — Proverbs 31:27*
