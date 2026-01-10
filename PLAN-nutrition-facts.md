# Plan: Complete Nutrition Facts Coverage

## Current State Analysis

| Status | Count | Percentage |
|--------|-------|------------|
| Complete | 126 | 9% |
| Partial | 324 | 24% |
| Insufficient Data | 309 | 23% |
| No nutrition field | ~579 | 43% |
| **Total recipes** | **1,338** | 100% |

**Existing infrastructure:**
- Schema: `nutrition.per_serving` with 7 macros (calories, fat_g, carbs_g, protein_g, sodium_mg, fiber_g, sugar_g)
- Display: `renderNutrition()` in script.js with styled grid layout
- Yield field: `servings_yield` already present in most recipes (e.g., "4 servings", "2 dozen cookies")

---

## Phase 1: Yield Normalization Script

**Goal:** Parse and normalize all `servings_yield` values to enable per-serving calculations.

### 1.1 Create `scripts/parse_yield.py`

```python
# Yield patterns to handle:
YIELD_PATTERNS = {
    # Standard servings
    r'(\d+)\s*servings?': lambda m: int(m.group(1)),
    r'serves\s*(\d+)': lambda m: int(m.group(1)),

    # Batch yields (cookies, muffins, etc.)
    r'(\d+)\s*dozen': lambda m: int(m.group(1)) * 12,
    r'(\d+)\s*cookies?': lambda m: int(m.group(1)),
    r'(\d+)\s*muffins?': lambda m: int(m.group(1)),
    r'(\d+)\s*cupcakes?': lambda m: int(m.group(1)),
    r'(\d+)\s*bars?': lambda m: int(m.group(1)),
    r'(\d+)\s*pieces?': lambda m: int(m.group(1)),
    r'(\d+)\s*slices?': lambda m: int(m.group(1)),
    r'(\d+)\s*portions?': lambda m: int(m.group(1)),

    # Volume yields (beverages, sauces)
    r'(\d+)\s*cups?': lambda m: int(m.group(1)),  # per 1-cup serving
    r'(\d+(?:/\d+)?)\s*gallons?': parse_gallon,   # 1 gallon = 16 cups
    r'(\d+)\s*quarts?': lambda m: int(m.group(1)) * 4,
    r'(\d+)\s*pints?': lambda m: int(m.group(1)) * 2,

    # Cake/pie yields
    r'(\d+)[- ]inch\s*(cake|pie)': lambda m: 8,  # Standard 8 slices
    r'one\s*(cake|pie|loaf)': lambda m: 8,
    r'(\d+)\s*(cakes?|pies?|loaves?)': lambda m: int(m.group(1)) * 8,
}
```

### 1.2 Add Normalized Field

Add `servings_count` (integer) to each recipe for calculation purposes:

```json
{
  "servings_yield": "2 dozen cookies",
  "servings_count": 24,
  ...
}
```

**Fallback logic:**
1. Parse `servings_yield` with regex patterns
2. If unparseable, estimate from category defaults:
   - Desserts (cookies/bars): 24
   - Cakes/pies: 8-12
   - Mains: 4-6
   - Beverages: varies by volume
3. Flag uncertain estimates with `confidence.flags`

---

## Phase 2: Nutrition Data Source

### 2.1 Option A: USDA FoodData Central (Recommended)

**Pros:**
- Free, no API key required for bulk download
- Comprehensive: 400,000+ foods
- Authoritative source
- Includes branded products

**Data files:**
- Download SR Legacy or Foundation Foods datasets
- Create local SQLite database for fast lookup

**Implementation:**
```python
# scripts/nutrition_db.py
import sqlite3

class NutritionDB:
    def __init__(self, db_path='data/nutrition.db'):
        self.conn = sqlite3.connect(db_path)

    def lookup(self, ingredient: str) -> dict:
        """Return nutrients per 100g for ingredient."""
        # Fuzzy matching with common substitutions
        # e.g., "butter" -> "BUTTER, SALTED"
        pass

    def calculate_recipe(self, ingredients: list, servings: int) -> dict:
        """Sum nutrients across ingredients, divide by servings."""
        pass
```

### 2.2 Option B: Nutritionix API

**Pros:**
- Natural language parsing ("2 cups flour")
- Handles mixed units automatically
- Good for complex/branded items

**Cons:**
- Rate limits on free tier (50 calls/day)
- Requires API key

### 2.3 Recommended Hybrid Approach

1. **Primary:** USDA FoodData Central (local database)
2. **Fallback:** Manual ingredient mapping table for regional/specialty items
3. **Complex items:** Flag for manual review

---

## Phase 3: Ingredient Parsing

### 3.1 Create `scripts/parse_ingredients.py`

Parse structured ingredient objects into calculable quantities:

```python
def parse_ingredient(ing: dict) -> tuple:
    """
    Returns: (ingredient_name, grams)

    Example:
    {"item": "flour", "quantity": "2", "unit": "cups"}
    -> ("all-purpose flour", 250g)
    """

    # Unit conversion table (to grams)
    CONVERSIONS = {
        'cup': {'flour': 125, 'sugar': 200, 'butter': 227, ...},
        'tbsp': {'butter': 14, 'oil': 13, 'flour': 8, ...},
        'tsp': {'salt': 6, 'baking powder': 4, ...},
        'oz': 28.35,  # weight oz
        'lb': 453.6,
        'stick': {'butter': 113},
        # Volume for liquids
        'cup_liquid': 237,  # ml ≈ g for water-based
    }

    # Handle edge cases
    # - "to taste" -> skip (negligible)
    # - "1-2 cups" -> use midpoint
    # - "[UNCLEAR]" -> flag as missing_input
```

### 3.2 Handle Grandma's Measurements

Special handling for vintage/regional terms:

| Term | Interpretation |
|------|----------------|
| "pinch" | 1/16 tsp |
| "dash" | 1/8 tsp |
| "handful" | ~1/4 cup |
| "heaping" | +25% |
| "scant" | -10% |
| "coffee cup" | 6 oz (vintage) |
| "jigger" | 1.5 oz |

---

## Phase 4: Calculation Script

### 4.1 Create `scripts/calculate_nutrition.py`

```python
def calculate_nutrition(recipe: dict, db: NutritionDB) -> dict:
    """
    Calculate nutrition facts for a recipe.

    Returns:
    {
        "status": "complete" | "partial" | "insufficient_data",
        "per_serving": {
            "calories": int,
            "fat_g": float,
            "carbs_g": float,
            "protein_g": float,
            "sodium_mg": float,
            "fiber_g": float,
            "sugar_g": float
        },
        "missing_inputs": [...],
        "assumptions": [...]
    }
    """

    servings = recipe.get('servings_count', estimate_servings(recipe))

    totals = {k: 0 for k in NUTRIENTS}
    missing = []
    assumptions = []

    for ing in recipe['ingredients']:
        try:
            name, grams = parse_ingredient(ing)
            nutrients = db.lookup(name)

            # Scale from per-100g to actual amount
            for nutrient in NUTRIENTS:
                totals[nutrient] += nutrients[nutrient] * (grams / 100)

        except IngredientNotFound:
            missing.append(ing['item'])
        except QuantityUnclear:
            assumptions.append(f"Estimated {ing['item']} quantity")

    # Divide by servings
    per_serving = {k: round(v / servings) for k, v in totals.items()}

    # Determine status
    if len(missing) == 0:
        status = "complete"
    elif len(missing) <= 2 and all_minor(missing):
        status = "partial"
        assumptions.append(f"Excludes: {', '.join(missing)}")
    else:
        status = "insufficient_data"

    return {
        "status": status,
        "per_serving": per_serving,
        "missing_inputs": missing,
        "assumptions": assumptions
    }
```

---

## Phase 5: Batch Processing

### 5.1 Create `scripts/enrich_nutrition.py`

Main orchestration script:

```python
def main():
    db = NutritionDB()
    recipes = load_recipes('data/recipes_master.json')

    stats = {'complete': 0, 'partial': 0, 'insufficient': 0, 'skipped': 0}

    for recipe in recipes:
        # Skip already-complete recipes
        if recipe.get('nutrition', {}).get('status') == 'complete':
            stats['skipped'] += 1
            continue

        nutrition = calculate_nutrition(recipe, db)
        recipe['nutrition'] = nutrition
        stats[nutrition['status']] += 1

    save_recipes('data/recipes_master.json', recipes)
    print_report(stats)
```

### 5.2 Validation & Review

After batch processing:

1. Run `python scripts/validate-recipes.py` to check schema
2. Spot-check 10-20 recipes manually
3. Review all `missing_inputs` entries for common patterns
4. Create ingredient mappings for frequently-missing items

---

## Phase 6: UI Enhancements (Optional)

### 6.1 Daily Value Percentages

Add %DV based on FDA 2,000 calorie diet:

```javascript
const DV = {
  fat_g: 78,
  carbs_g: 275,
  protein_g: 50,
  sodium_mg: 2300,
  fiber_g: 28,
  sugar_g: 50  // Added sugars limit
};

function renderNutritionWithDV(nutrition) {
  // Show both absolute and percentage
  // e.g., "Fat: 9g (12% DV)"
}
```

### 6.2 Nutrition Label Format

Optional: Render as FDA-style nutrition facts label for print/ebook.

### 6.3 Dietary Filters

Add filters on index page:
- Low calorie (< 300/serving)
- Low carb (< 20g)
- High protein (> 20g)
- Low sodium (< 500mg)

---

## Implementation Order

| Step | Task | Effort |
|------|------|--------|
| 1 | Download USDA FoodData Central, create SQLite DB | Medium |
| 2 | Create `parse_yield.py`, normalize all yields | Low |
| 3 | Create `parse_ingredients.py` with unit conversions | Medium |
| 4 | Create ingredient mapping table for specialty items | Medium |
| 5 | Create `calculate_nutrition.py` core logic | Medium |
| 6 | Create `enrich_nutrition.py` batch processor | Low |
| 7 | Run batch enrichment, review results | Low |
| 8 | Add ingredient mappings for missing items, re-run | Medium |
| 9 | Manual review of edge cases | Medium |
| 10 | (Optional) UI enhancements | Low |

---

## Success Criteria

- [ ] 80%+ recipes have "complete" nutrition status
- [ ] Remaining 20% have "partial" with documented assumptions
- [ ] Zero recipes have empty nutrition field
- [ ] All calculations validated against 10+ known recipes
- [ ] Missing ingredient mappings documented for future updates

---

## Notes on Accuracy

Per CLAUDE.md: **"Accuracy is more important than speed."**

- Always round to whole numbers (no false precision)
- Document all assumptions clearly
- Flag uncertain estimates rather than guess
- Use conservative estimates for "to taste" ingredients
- Cross-reference with original recipe cards where nutrition was printed

---

## Appendix: Yield Inference by Category

When `servings_yield` is unparseable, use category defaults:

| Category | Default Servings | Notes |
|----------|------------------|-------|
| appetizers | 8 | party-sized |
| beverages | 8 cups | per 1/2 gallon |
| breads | 12 slices | per loaf |
| breakfast | 4 | family-sized |
| desserts (cookies) | 24 | per batch |
| desserts (cake/pie) | 8 | per 9" round |
| desserts (bars) | 16 | per 9x13 pan |
| mains | 4 | family-sized |
| salads | 6 | side portions |
| sides | 6 | family-sized |
| soups | 8 cups | per pot |
| snacks | 12 | party-sized |
