# Pending Tasks & Feature Requests

This file tracks future development tasks, feature requests, and research items for the Grandma's Kitchen Family Recipe Archive.

---

## High Priority

### Protein & Vegetable Substitution Tool

**Status:** Research Required
**Added:** 2026-01-23
**Complexity:** High

Create an interactive tool that helps users substitute proteins or vegetables in recipes, with guidance on how substitutions affect the final dish.

#### Requirements

1. **Protein Substitutions**
   - Beef ↔ Pork ↔ Chicken ↔ Turkey ↔ Lamb
   - Fish ↔ Shellfish (shrimp, scallops, etc.)
   - Tofu/Tempeh as vegetarian alternatives
   - Cooking time adjustments per protein
   - Internal temperature requirements
   - Texture/flavor impact notes

2. **Seafood Substitutions**
   - White fish varieties (cod, tilapia, halibut, etc.)
   - Fatty fish varieties (salmon, mackerel, tuna)
   - Shellfish (shrimp ↔ scallops ↔ crab ↔ lobster)
   - Fresh vs frozen considerations
   - Mercury content warnings where applicable

3. **Vegetable Substitutions**
   - Moisture content warnings (e.g., "Adding tomatoes to Alfredo will make it soupy")
   - Cooking time differences
   - Texture impact (crispy vs soft)
   - Flavor profile changes (bitter, sweet, earthy)
   - Starch content considerations (potatoes vs cauliflower)

4. **Research Areas**
   - Fat content differences between proteins
   - How different proteins absorb marinades
   - Collagen content and braising requirements
   - Vegetable water release during cooking
   - Acidity interactions (tomatoes with cream sauces)
   - Starch release and sauce thickening

#### Data Structure (Proposed)

```json
{
  "protein_substitutions": {
    "chicken_breast": {
      "cook_time_per_lb": "20-25 min at 375°F",
      "internal_temp": "165°F",
      "substitutes": [
        {
          "protein": "turkey_breast",
          "ratio": "1:1",
          "cook_time_adjustment": "+5-10 min",
          "notes": "Drier, may need more moisture"
        },
        {
          "protein": "pork_tenderloin",
          "ratio": "1:1",
          "cook_time_adjustment": "similar",
          "notes": "Slightly sweeter, pairs well with fruit"
        }
      ]
    }
  },
  "vegetable_substitutions": {
    "tomatoes": {
      "water_content": "high",
      "acidity": "high",
      "warnings": [
        {
          "context": "cream_sauce",
          "warning": "High water content will thin the sauce. Acidity may cause curdling.",
          "mitigation": "Use sun-dried or roasted tomatoes, add at end"
        }
      ],
      "substitutes": [
        {
          "vegetable": "roasted_red_peppers",
          "ratio": "1:1 by volume",
          "notes": "Sweeter, less acidic, similar texture when roasted"
        }
      ]
    }
  }
}
```

#### Implementation Notes

- Consider integrating with existing milk-substitution.js architecture
- Should trigger based on ingredient detection in recipes
- Display warnings prominently (e.g., "This substitution may affect texture")
- Allow users to see "before/after" impact summary

#### Research Sources to Consult

- [ ] USDA food composition database (protein fat/moisture content)
- [ ] Serious Eats articles on protein substitution
- [ ] America's Test Kitchen substitution guides
- [ ] Harold McGee's "On Food and Cooking"
- [ ] Kenji López-Alt's "The Food Lab"

---

## Medium Priority

### Recipe Scaling Intelligence

**Status:** Planned
**Added:** 2026-01-23

Improve recipe scaling beyond simple multiplication:
- Spice/seasoning scaling (often non-linear)
- Pan size recommendations for scaled recipes
- Cooking time adjustments for larger batches
- Warnings for recipes that don't scale well (soufflés, etc.)

---

### Nutrition Estimation Improvements

**Status:** Planned
**Added:** 2026-01-23

- Add more cheese-making specific nutrition data
- Handle "to taste" ingredients better
- Support nutrition comparison between original and substituted versions

---

### Offline PWA Enhancements

**Status:** Planned
**Added:** 2026-01-23

- Add offline indicator in UI
- Cache user's favorite recipes automatically
- Sync favorites when back online
- Better offline search support

---

## Low Priority / Future Ideas

### Print Cookbook Generation

Generate printable PDF cookbooks from selected recipes:
- Support for different paper sizes
- Index generation
- Family dedication pages

### Voice Assistant Integration

"Hey Grandma, what can I make with chicken and broccoli?"
- Research Alexa/Google Home integration
- Voice-guided cooking mode

### Recipe Difficulty Rating

Automatically estimate recipe difficulty based on:
- Number of techniques required
- Ingredient complexity
- Time requirements
- Equipment needed

---

## Completed Tasks

| Task | Completed | Notes |
|------|-----------|-------|
| Add 2,013 cheese recipes from Allrecipes | 2026-01-23 | Aggregated via aggregate_collections.py |
| Create service worker for PWA | 2026-01-23 | sw.js with multi-repo caching |
| Document adulterant companion tool | 2026-01-23 | ADULTERANT-COMPANION-GUIDE.md |
| Optimize index loading (12MB → 3.7MB) | 2026-01-23 | Removed ingredients from index |
| Add cheese category filter | 2026-01-23 | Navigation updated |
| Add cheese builder link | 2026-01-23 | Links to Allrecipes tool |

---

## Research Notes

### Protein Substitution Factors (Initial Research)

| Factor | Impact | Example |
|--------|--------|---------|
| Fat content | Moisture, richness | Pork shoulder vs chicken breast |
| Connective tissue | Braising requirements | Beef chuck needs low-slow |
| Grain/texture | Slicing direction matters | Against grain for tenderness |
| Myoglobin | Color when cooked | Beef stays pink longer |
| Size/thickness | Cook time per lb varies | Whole chicken vs parts |

### Vegetable Water Content (Initial Data)

| Vegetable | Water % | Cooking Impact |
|-----------|---------|----------------|
| Tomatoes | 94% | Will thin sauces significantly |
| Cucumbers | 96% | Releases water when salted |
| Zucchini | 95% | Sweats when heated, needs draining |
| Mushrooms | 92% | Shrinks dramatically, releases liquid |
| Carrots | 88% | More stable, good for long cooking |
| Potatoes | 79% | Releases starch, thickens sauces |
| Onions | 89% | Caramelizes, sweetens when cooked |

---

*"She looketh well to the ways of her household, and eateth not the bread of idleness." — Proverbs 31:27*
