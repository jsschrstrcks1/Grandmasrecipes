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

### Diabetic-Friendly Recipe Converter

**Status:** Research Required
**Added:** 2026-01-23
**Complexity:** High

Create a tool that converts recipes to diabetic-friendly versions by reducing carbs and sugar while increasing protein, with minimal impact on taste.

#### Goals

- Target: **Under 50g carbs per serving** for converted recipes
- Maintain flavor profile as close to original as possible
- Increase protein content where possible
- Provide glycemic index estimates

#### Carb Substitution Categories

**1. Pasta & Noodles**
| Original | Substitute | Carbs Saved | Protein Change | Taste Notes |
|----------|------------|-------------|----------------|-------------|
| Regular pasta (40g/cup) | Zucchini noodles | ~38g | Similar | Lighter, needs salting to remove moisture |
| Regular pasta | Shirataki noodles | ~38g | Similar | Neutral taste, different texture |
| Regular pasta | Palmini (hearts of palm) | ~36g | Similar | Slightly tangy, pasta-like texture |
| Regular pasta | Spaghetti squash | ~35g | Similar | Slightly sweet, stringy texture |
| Regular pasta | Edamame pasta | ~20g | +12g protein | Slight bean flavor, holds sauce well |
| Regular pasta | Chickpea pasta | ~25g | +8g protein | Nutty flavor, firmer texture |

**2. Rice & Grains**
| Original | Substitute | Carbs Saved | Notes |
|----------|------------|-------------|-------|
| White rice (45g/cup) | Cauliflower rice | ~40g | Needs seasoning, releases water |
| White rice | Broccoli rice | ~40g | More flavor than cauliflower |
| White rice | Shirataki rice | ~43g | Neutral, good for stir-fry |
| Couscous | Cauliflower couscous | ~35g | Pulse cauliflower fine |
| Quinoa | Hemp hearts | ~10g | Much higher protein |

**3. Bread & Baking**
| Original | Substitute | Carbs Saved | Notes |
|----------|------------|-------------|-------|
| All-purpose flour | Almond flour | ~20g/cup | Denser, nuttier, needs more eggs |
| All-purpose flour | Coconut flour | ~18g/cup | Very absorbent, use 1/4 amount |
| All-purpose flour | Lupin flour | ~22g/cup | High protein, slight bitterness |
| Breadcrumbs | Pork rind crumbs | ~15g/cup | Zero carb, very crunchy |
| Breadcrumbs | Almond meal | ~12g/cup | Nuttier flavor |
| Bread (sandwich) | Lettuce wraps | ~12g/slice | Fresh, crisp, no bread flavor |
| Bread | Cloud bread (eggs+cream cheese) | ~12g/slice | Light, eggy |
| Tortillas | Cheese wraps | ~15g | Made from baked cheese |
| Tortillas | Egg wraps | ~14g | Thin omelet style |

**4. Potatoes & Starches**
| Original | Substitute | Carbs Saved | Notes |
|----------|------------|-------------|-------|
| Mashed potatoes | Mashed cauliflower | ~20g/cup | Add cream cheese for richness |
| Mashed potatoes | Mashed turnips | ~15g/cup | Slightly peppery |
| French fries | Jicama fries | ~15g | Crispy when baked, slightly sweet |
| French fries | Rutabaga fries | ~12g | Earthy, roasts well |
| Hash browns | Radish hash browns | ~18g | Mellows when cooked |
| Potato chips | Cheese crisps | ~15g | Baked parmesan or cheddar |
| Potato chips | Zucchini chips | ~14g | Dehydrated or baked |

**5. Sugars & Sweeteners**
| Original | Substitute | Carb Impact | Notes |
|----------|------------|-------------|-------|
| Sugar (1 cup = 200g carbs) | Erythritol | -200g | 70% sweetness, cooling effect |
| Sugar | Monk fruit | -200g | 150-200x sweeter, use tiny amounts |
| Sugar | Allulose | -200g | 70% sweetness, browns like sugar |
| Sugar | Stevia | -200g | 200-300x sweeter, slight aftertaste |
| Honey | Sugar-free maple syrup | -17g/tbsp | Check for maltitol (GI issues) |
| Brown sugar | Swerve brown | -13g/tbsp | Erythritol + molasses flavor |

**6. Thickeners**
| Original | Substitute | Notes |
|----------|------------|-------|
| Flour (for sauces) | Xanthan gum | Use 1/8 tsp per cup liquid |
| Flour | Glucomannan | Very powerful, use sparingly |
| Cornstarch | Guar gum | 1/8 the amount needed |

#### Implementation Features

1. **Auto-Detection**
   - Scan recipe ingredients for high-carb items
   - Calculate total carbs per serving
   - Flag recipes over 50g carbs

2. **Conversion Suggestions**
   - Show side-by-side: original vs converted
   - Display carb savings per substitution
   - Protein increase where applicable
   - Taste/texture warnings

3. **Glycemic Index Tracking**
   - Estimate GI of original recipe
   - Show GI reduction with substitutions
   - Flag high-GI ingredients

4. **User Preferences**
   - Allow exclusions (e.g., "no artificial sweeteners")
   - Allergen awareness (nut flours, etc.)
   - Strictness levels: Keto (<20g), Low-carb (<50g), Moderate (<100g)

#### Data Structure (Proposed)

```json
{
  "carb_substitutions": {
    "pasta": {
      "original_carbs_per_cup": 43,
      "substitutes": [
        {
          "name": "zucchini_noodles",
          "carbs_per_cup": 4,
          "protein_per_cup": 1.5,
          "prep_notes": "Spiralize, salt and drain 10 min to remove moisture",
          "cooking_notes": "Sauté 2-3 min max or serve raw",
          "taste_impact": "lighter, fresher, less filling",
          "best_for": ["light sauces", "pesto", "olive oil based"],
          "avoid_for": ["heavy cream sauces (gets watery)"]
        },
        {
          "name": "shirataki_noodles",
          "carbs_per_cup": 1,
          "protein_per_cup": 0,
          "fiber_per_cup": 3,
          "prep_notes": "Rinse thoroughly, dry-fry to remove moisture",
          "cooking_notes": "Absorbs sauce flavors well",
          "taste_impact": "neutral, slightly chewy texture",
          "best_for": ["Asian dishes", "soups", "heavy sauces"]
        }
      ]
    }
  },
  "sweetener_conversions": {
    "sugar": {
      "erythritol": { "ratio": "1:1.3", "notes": "70% as sweet" },
      "monk_fruit": { "ratio": "1 cup : 1 tsp", "notes": "Very concentrated" },
      "allulose": { "ratio": "1:1.3", "notes": "Browns well, 70% sweet" }
    }
  }
}
```

#### Research Required

- [ ] Complete carb counts for all common ingredients
- [ ] Glycemic index database integration
- [ ] Baking chemistry: how substitutes affect rise, texture
- [ ] Sauce thickening ratios for alternative thickeners
- [ ] Sweetener heat stability (some break down when baked)
- [ ] Fiber content (net carbs = total carbs - fiber)

#### Integration with Existing Tools

- Link with nutrition estimation (show before/after macros)
- Integrate with protein substitution tool
- Consider meal planning features (daily carb totals)

#### Detailed Implementation Plan

**Phase 1: Data Foundation**

1. **Build Ingredient Carb Database** (`data/carb-database.json`)
   - Total carbs, fiber, net carbs per standard serving
   - Glycemic index and glycemic load
   - Protein content for macro balancing
   - Source: USDA FoodData Central API

2. **Build Substitution Rules** (`data/diabetic-substitutions.json`)
   - Category-based substitutions (pasta, bread, rice, etc.)
   - Context-aware rules (don't suggest zucchini noodles for lasagna)
   - Ratio conversions and prep instructions
   - Taste/texture impact ratings (1-5 scale)

3. **Recipe Analysis Function**
   ```javascript
   function analyzeRecipeCarbs(recipe) {
     // Parse ingredients, match to carb database
     // Calculate per-serving macros
     // Return { totalCarbs, fiber, netCarbs, protein, gi_estimate }
   }
   ```

**Phase 2: Core Converter Logic**

1. **Ingredient Parser Enhancement**
   - Detect quantities and units accurately
   - Handle variations ("1 cup pasta, cooked" vs "8 oz dry pasta")
   - Identify high-carb ingredients automatically

2. **Substitution Engine** (`diabetic-converter.js`)
   ```javascript
   class DiabeticConverter {
     constructor(recipe, targetNetCarbs = 50) { }

     // Analyze current recipe
     analyze() { return { perServing: {...}, flaggedIngredients: [...] }; }

     // Get substitution options for each flagged ingredient
     getSuggestions(ingredient) { return [...substitutes]; }

     // Apply substitutions and recalculate
     applySubstitution(ingredientIndex, substituteId) { }

     // Generate converted recipe with adjusted instructions
     generateConvertedRecipe() { return { recipe, carbSavings, notes }; }
   }
   ```

3. **Smart Substitution Selection**
   - Consider recipe context (Italian → zucchini noodles, Asian → shirataki)
   - Avoid conflicting substitutions
   - Warn about texture/taste changes
   - Suggest complementary adjustments (add fat for satiety)

**Phase 3: User Interface**

1. **Recipe Page Integration**
   - "Make Diabetic-Friendly" button on high-carb recipes
   - Side-by-side comparison view
   - Interactive ingredient swapping
   - Real-time macro updates

2. **Visual Indicators**
   ```html
   <div class="diabetic-panel">
     <div class="carb-meter">
       <span class="original">Original: 78g carbs</span>
       <span class="converted">Converted: 12g carbs</span>
       <div class="savings-badge">-85% carbs</div>
     </div>
     <div class="macro-comparison">
       <!-- Before/after protein, fat, fiber -->
     </div>
   </div>
   ```

3. **Substitution Cards**
   - Show each swap with explanation
   - Prep instructions for substitute
   - "Why this works" explanation
   - User can accept/reject each suggestion

**Phase 4: Advanced Features**

1. **Strictness Levels**
   | Level | Target Net Carbs | Use Case |
   |-------|------------------|----------|
   | Keto | <20g/serving | Strict ketogenic diet |
   | Low-Carb | <50g/serving | General diabetic-friendly |
   | Moderate | <100g/serving | Carb-conscious |
   | Custom | User-defined | Personalized goals |

2. **Meal Planning Integration**
   - Track daily carb totals across meals
   - Suggest recipes to balance the day
   - "I have 30g carbs left for dinner" search

3. **Blood Sugar Impact Estimation**
   - Use glycemic load calculations
   - Show estimated blood sugar curve
   - Flag rapid-spike ingredients

4. **Print/Export**
   - Export converted recipe as new entry
   - Print diabetic-friendly version
   - Share conversion with notes

**Phase 5: Quality Assurance**

1. **Taste Testing Notes Database**
   - Crowdsource feedback on substitutions
   - Rate: "Tastes like original" (1-5)
   - Collect tips from users

2. **Edge Cases to Handle**
   - Baking: leavening affected by flour swaps
   - Sauces: thickening without flour/cornstarch
   - Desserts: sweetener + bulk replacement
   - Bread: gluten structure without wheat

3. **Warning System**
   ```javascript
   const warnings = [
     { type: 'texture', message: 'Almond flour makes denser baked goods' },
     { type: 'baking', message: 'Reduce oven temp 25°F for almond flour' },
     { type: 'sweetener', message: 'Erythritol may crystallize in cold desserts' },
     { type: 'digestive', message: 'Sugar alcohols may cause GI discomfort in large amounts' }
   ];
   ```

#### File Structure (Proposed)

```
Grandmasrecipes/
├── diabetic-converter.js       # Core conversion logic
├── data/
│   ├── carb-database.json      # Ingredient carb/GI data
│   ├── diabetic-substitutions.json  # Substitution rules
│   └── sweetener-ratios.json   # Baking conversion ratios
└── styles.css                  # Add .diabetic-* styles
```

#### API Design

```javascript
// Initialize converter for a recipe
const converter = new DiabeticConverter(recipe, {
  targetNetCarbs: 50,
  strictness: 'low-carb',
  excludeSubstitutes: ['artificial-sweeteners'],
  preferences: {
    preferWholeFoods: true,
    avoidNutFlours: false
  }
});

// Analyze and get suggestions
const analysis = converter.analyze();
// {
//   currentNetCarbs: 78,
//   currentProtein: 12,
//   flaggedIngredients: [
//     { index: 2, name: 'pasta', carbs: 43, suggestions: [...] }
//   ]
// }

// Apply a substitution
converter.applySubstitution(2, 'zucchini-noodles');

// Get final converted recipe
const result = converter.generateConvertedRecipe();
// {
//   recipe: { ...modifiedRecipe },
//   carbSavings: 39,
//   proteinChange: +2,
//   warnings: [...],
//   prepNotes: ['Spiralize zucchini, salt and drain 10 min...']
// }
```

#### Success Metrics

- [ ] 90%+ of pasta recipes convertible to <20g carbs
- [ ] 80%+ of bread recipes convertible to <50g carbs
- [ ] User taste satisfaction >3.5/5 average
- [ ] <5% of conversions require manual override

#### Dependencies

- Nutrition estimation tool (for macro calculations)
- Ingredient parser (for quantity extraction)
- Recipe scaling (for serving size adjustments)

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
