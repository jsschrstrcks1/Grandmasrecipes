# Pending Tasks & Feature Requests

This file tracks future development tasks, feature requests, and research items for the Grandma's Kitchen Family Recipe Archive.

---

## High Priority

### Protein & Vegetable Substitution Tool

**Status:** Data Foundation Complete - UI Implementation Pending
**Added:** 2026-01-23
**Updated:** 2026-01-28
**Complexity:** High

Create an interactive tool that helps users substitute proteins or vegetables in recipes, with guidance on how substitutions affect the final dish.

#### Completed (2026-01-28)

**Data file created:** `data/protein-vegetable-substitutions.json`

Contains comprehensive substitution data for:
- **Protein substitutions:** chicken breast, chicken thighs, ground beef, beef stew meat, beef roast, bacon - with ratios, cook time adjustments, flavor notes, and plant-based alternatives
- **Fish substitutions:** 4 texture categories (delicate/flaky, firm/mild, meaty/bold, fatty/rich) with specific fish and substitutes
- **Shellfish substitutions:** shrimp, scallops, lobster, crab with alternatives including plant-based options
- **Mercury guide:** FDA best choices, good choices, and fish to avoid
- **Vegetable moisture warnings:** zucchini, tomatoes, mushrooms, cucumbers, eggplant with mitigation strategies
- **Vegetable texture substitutions:** leafy greens, root vegetables, cruciferous, alliums
- **Acidity interactions:** tomatoes with cream, citrus with dairy
- **Safe cooking temperatures:** USDA guidelines for all proteins
- **Roasting time charts:** beef, pork, chicken, turkey, lamb (min/max per lb)
- **Plant protein reference:** complete proteins and combining guidelines

**Research sources used:**
- [USDA FSIS Safe Temperature Chart](https://www.fsis.usda.gov/food-safety/safe-food-handling-and-preparation/food-safety-basics/safe-temperature-chart)
- [FDA Advice About Eating Fish](https://www.fda.gov/food/consumers/advice-about-eating-fish)
- [FoodSafety.gov Roasting Charts](https://www.foodsafety.gov/food-safety-charts/meat-poultry-charts)
- [Cook Smarts Ingredient Substitutions](https://www.cooksmarts.com/articles/substitute-ingredients-meat-cuts-and-seafood/)
- [America's Test Kitchen - Salting Watery Vegetables](https://www.americastestkitchen.com/articles/4102-why-you-should-salt-watery-vegetables-before-cooking)

#### Next Steps: UI Implementation

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

3. **Vegetable Protein Substitutions** (Plant-Based)
   | Protein Source | Protein/Serving | Complete? | Best For | Notes |
   |----------------|-----------------|-----------|----------|-------|
   | Tofu (firm) | 20g/cup | Yes | Stir-fry, grilling, scrambles | Press to remove water, absorbs marinades |
   | Tempeh | 31g/cup | Yes | Grilling, crumbling, slicing | Fermented, nuttier flavor, firmer texture |
   | Seitan | 25g/100g | No* | Stews, stir-fry, "meat" dishes | *Cook in soy sauce broth for complete protein |
   | Lentils | 18g/cup | No | Soups, curries, meat extender | Combine with rice for complete protein |
   | Chickpeas | 15g/cup | No | Curries, salads, hummus | Very versatile, good texture |
   | Black beans | 15g/cup | No | Tacos, burgers, soups | Combine with corn/rice |
   | Edamame | 17g/cup | Yes | Salads, snacks, stir-fry | Young soybeans, mild flavor |
   | Quinoa | 8g/cup | Yes | Grain substitute, salads | Also a complete protein grain |
   | Hemp seeds | 10g/3tbsp | Yes | Toppings, smoothies | Nutty flavor, omega-3s |
   | Nutritional yeast | 8g/2tbsp | Yes | Cheese flavor, sauces | B12 fortified usually |

   **Protein Combining for Complete Proteins:**
   - Legumes + Grains = Complete (beans + rice, lentils + bread)
   - Legumes + Seeds = Complete (hummus with tahini)
   - Legumes + Nuts = Complete (bean salad with walnuts)

4. **Vegetable Substitutions**
   - Moisture content warnings (e.g., "Adding tomatoes to Alfredo will make it soupy")
   - Cooking time differences
   - Texture impact (crispy vs soft)
   - Flavor profile changes (bitter, sweet, earthy)
   - Starch content considerations (potatoes vs cauliflower)

5. **Research Areas**
   - Fat content differences between proteins
   - How different proteins absorb marinades
   - Collagen content and braising requirements
   - Vegetable water release during cooking
   - Acidity interactions (tomatoes with cream sauces)
   - Starch release and sauce thickening
   - Plant protein digestibility (PDCAAS scores)
   - Anti-nutrients in legumes (phytates, lectins) and how to reduce them

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

#### Research Sources Consulted

- [x] USDA food composition database (protein fat/moisture content)
- [x] USDA FSIS safe cooking temperatures
- [x] FDA fish mercury guidelines
- [x] America's Test Kitchen substitution guides
- [x] Cook Smarts ingredient substitution guides
- [x] FoodSafety.gov roasting charts
- [ ] Harold McGee's "On Food and Cooking" (for future expansion)
- [ ] Kenji López-Alt's "The Food Lab" (for future expansion)

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

### Heart-Smart Recipe Converter

**Status:** Research Required
**Added:** 2026-01-23
**Complexity:** High

Create a tool that converts recipes to heart-healthy versions by reducing sodium, saturated fat, and cholesterol while maintaining flavor through herbs, spices, and healthy fat substitutions.

#### Goals

- Target: **Under 600mg sodium per serving** (AHA recommendation)
- Target: **Under 13g saturated fat per serving** (based on 2000 cal diet)
- Target: **Under 300mg cholesterol per day** (general guideline)
- Increase omega-3 fatty acids where possible
- Increase fiber content
- Maintain flavor through herb/spice enhancement

#### Heart Health Targets (Per Serving)

| Metric | Target | Danger Zone | Notes |
|--------|--------|-------------|-------|
| Sodium | <600mg | >1500mg | AHA recommends <2300mg/day total |
| Saturated Fat | <5g | >13g | <10% of daily calories |
| Trans Fat | 0g | Any | Avoid completely |
| Cholesterol | <100mg | >200mg | <300mg/day total |
| Fiber | >5g | <2g | 25-30g/day recommended |
| Added Sugar | <6g | >12g | AHA: <25g/day women, <36g men |

#### Sodium Reduction Strategies

**1. Salt Substitutions**
| Original | Substitute | Sodium Saved | Flavor Notes |
|----------|------------|--------------|--------------|
| 1 tsp salt (2300mg) | 1/2 tsp salt + herbs | ~1150mg | Use fresh herbs generously |
| 1 tsp salt | Salt-free seasoning blend | ~2300mg | Mrs. Dash, homemade blends |
| 1 tsp salt | 1/4 tsp salt + acid (lemon/vinegar) | ~1725mg | Acid brightens without salt |
| 1 tsp salt | Potassium chloride (Nu-Salt) | ~2300mg | Slightly bitter, use 1/2 amount |

**2. High-Sodium Ingredient Swaps**
| Original | Sodium | Substitute | Sodium | Savings |
|----------|--------|------------|--------|---------|
| Soy sauce (1 tbsp) | 920mg | Low-sodium soy | 575mg | 345mg |
| Soy sauce (1 tbsp) | 920mg | Coconut aminos | 90mg | 830mg |
| Canned beans (1 cup) | 400mg | Rinse 1 min / dried | 150mg / 0mg | 250-400mg |
| Canned tomatoes | 300mg | No-salt-added | 25mg | 275mg |
| Chicken broth (1 cup) | 860mg | Low-sodium broth | 140mg | 720mg |
| Chicken broth | 860mg | Homemade unsalted | 70mg | 790mg |
| Bacon (2 slices) | 370mg | Turkey bacon | 180mg | 190mg |
| Bacon | 370mg | Uncured, low-sodium | 150mg | 220mg |
| Parmesan (1 oz) | 450mg | Nutritional yeast | 10mg | 440mg |
| Feta (1 oz) | 320mg | Goat cheese | 130mg | 190mg |
| Pickles | 800mg | Quick-pickled (low salt) | 200mg | 600mg |

**3. Flavor Enhancement (Salt-Free)**
| Technique | Examples | Best For |
|-----------|----------|----------|
| Acid brightness | Lemon, lime, vinegar, wine | Finish dishes, cut richness |
| Umami depth | Mushrooms, tomato paste, miso (low-sodium) | Savory dishes, soups |
| Fresh herbs | Basil, cilantro, parsley, dill | Added at end for brightness |
| Dried herbs | Oregano, thyme, rosemary | Cooked into dishes |
| Spice heat | Black pepper, cayenne, crushed red pepper | Awakens palate |
| Aromatics | Garlic, onion, shallots, ginger | Sautéed as base |
| Toasted elements | Nuts, seeds, spices (dry-toasted) | Adds complexity |

#### Fat Substitutions

**1. Saturated Fat Swaps**
| Original | Sat Fat | Substitute | Sat Fat | Notes |
|----------|---------|------------|---------|-------|
| Butter (1 tbsp) | 7g | Olive oil | 2g | Better for sautéing |
| Butter | 7g | Avocado oil | 1.6g | High smoke point |
| Butter | 7g | Ghee (clarified) | 8g | NOT lower, but lactose-free |
| Butter (baking) | 7g | Applesauce (1/2 amt) | 0g | Adds moisture, reduce sugar |
| Butter (baking) | 7g | Greek yogurt | 0.5g | Tangy, keeps moisture |
| Cream (1 cup) | 28g | Evaporated milk | 5g | Still creamy, less rich |
| Cream | 28g | Cashew cream | 2g | Blend soaked cashews |
| Cream | 28g | Silken tofu blended | 0.5g | Neutral flavor |
| Cream cheese (1 oz) | 6g | Neufchâtel | 4g | 1/3 less fat |
| Cream cheese | 6g | Greek yogurt + cream cheese (1:1) | 3g | Tangy, lighter |
| Sour cream | 3g/tbsp | Greek yogurt | 0.5g/tbsp | Nearly identical taste |
| Whole milk | 5g/cup | 2% milk | 3g/cup | Minimal taste difference |
| Whole milk | 5g/cup | Skim + 1 tbsp oil | 1.5g | For baking |
| Coconut milk | 48g/cup | Light coconut milk | 13g | Still creamy |
| Ground beef 80/20 | 8g/3oz | 93/7 lean | 3g | Brown with onions for moisture |
| Ground beef | 8g/3oz | Ground turkey 93/7 | 2.5g | Season well |
| Pork sausage | 8g/link | Chicken sausage | 2g | Look for low-sodium |
| Bacon | 3g/slice | Canadian bacon | 0.8g | Leaner, less smoky |

**2. Cholesterol Swaps**
| Original | Cholesterol | Substitute | Cholesterol | Notes |
|----------|-------------|------------|-------------|-------|
| 1 whole egg (186mg) | 186mg | 2 egg whites | 0mg | Lose richness, add 1 yolk per 3 eggs |
| 1 egg | 186mg | Flax egg (1T flax + 3T water) | 0mg | Baking only |
| 1 egg | 186mg | 1/4 cup aquafaba | 0mg | Chickpea liquid, meringues |
| Shrimp (3oz) | 166mg | Scallops | 28mg | Similar texture |
| Liver (3oz) | 330mg | Avoid | — | Extremely high cholesterol |

**3. Increase Omega-3s**
| Addition | Omega-3 | How to Use |
|----------|---------|------------|
| Salmon (3oz) | 1.5g | Replace other proteins 2x/week |
| Sardines | 1.8g/3oz | Add to salads, pastas |
| Walnuts (1oz) | 2.5g | Top salads, oatmeal |
| Flaxseed (1 tbsp) | 1.6g | Add to smoothies, baking |
| Chia seeds (1 tbsp) | 1.7g | Puddings, oatmeal |
| Hemp hearts (3 tbsp) | 3g | Top anything |

#### Fiber Boosting

| Addition | Fiber | How to Add |
|----------|-------|------------|
| Beans (1/2 cup) | 7g | Add to soups, salads, any dish |
| Lentils (1/2 cup) | 8g | Bulk up meat dishes |
| Oats (1/2 cup) | 4g | Meatloaf binder, smoothies |
| Chia seeds (2 tbsp) | 10g | Puddings, baked goods |
| Flaxseed (2 tbsp) | 4g | Baking, smoothies |
| Avocado (1/2) | 5g | Top dishes, replace mayo |
| Raspberries (1 cup) | 8g | Desserts, breakfast |
| Artichoke hearts | 7g/cup | Add to pasta, salads |

#### Implementation Plan

**Phase 1: Data Foundation**

```json
// data/heart-smart-database.json
{
  "ingredients": {
    "salt": {
      "sodium_per_tsp_mg": 2300,
      "heart_concern": "primary",
      "substitutes": [
        {
          "name": "reduced_salt_with_herbs",
          "ratio": "1 tsp : 1/2 tsp salt + 1 tsp herb blend",
          "sodium_reduction_mg": 1150,
          "flavor_notes": "Use Italian herbs for pasta, herbs de Provence for French"
        }
      ]
    },
    "butter": {
      "saturated_fat_per_tbsp_g": 7,
      "cholesterol_per_tbsp_mg": 31,
      "heart_concerns": ["saturated_fat", "cholesterol"],
      "substitutes": [...]
    }
  }
}
```

**Phase 2: Heart-Smart Analyzer**

```javascript
class HeartSmartConverter {
  constructor(recipe, targets = {}) {
    this.recipe = recipe;
    this.targets = {
      maxSodiumPerServing: targets.sodium || 600,
      maxSatFatPerServing: targets.satFat || 5,
      maxCholesterolPerServing: targets.cholesterol || 100,
      minFiberPerServing: targets.fiber || 5,
      ...targets
    };
  }

  analyze() {
    return {
      currentSodium: this.calculateSodium(),
      currentSatFat: this.calculateSatFat(),
      currentCholesterol: this.calculateCholesterol(),
      currentFiber: this.calculateFiber(),
      concerns: this.identifyConcerns(), // ['high_sodium', 'high_sat_fat']
      flaggedIngredients: this.flagIngredients()
    };
  }

  getSuggestions(ingredient) {
    // Return substitution options sorted by health impact
  }

  applySubstitution(ingredientIndex, substituteId) {
    // Apply and recalculate all metrics
  }

  addFlavorEnhancers() {
    // Suggest herbs/spices to compensate for reduced salt
    return [
      { add: "1 tbsp fresh lemon juice", reason: "Brightens without sodium" },
      { add: "1/2 tsp black pepper", reason: "Adds bite, enhances flavor" },
      { add: "2 cloves garlic, minced", reason: "Umami depth" }
    ];
  }

  generateHeartSmartRecipe() {
    return {
      recipe: this.modifiedRecipe,
      improvements: {
        sodiumReduction: `${this.originalSodium - this.newSodium}mg`,
        satFatReduction: `${this.originalSatFat - this.newSatFat}g`,
        fiberIncrease: `+${this.newFiber - this.originalFiber}g`
      },
      warnings: this.warnings,
      flavorEnhancements: this.suggestedEnhancements
    };
  }
}
```

**Phase 3: Combined Converter (Heart-Smart + Diabetic)**

```javascript
class HealthyRecipeConverter {
  constructor(recipe, options = {}) {
    this.recipe = recipe;
    this.diabeticMode = options.diabetic || false;
    this.heartSmartMode = options.heartSmart || false;

    if (this.diabeticMode) {
      this.diabeticConverter = new DiabeticConverter(recipe, options.diabeticTargets);
    }
    if (this.heartSmartMode) {
      this.heartSmartConverter = new HeartSmartConverter(recipe, options.heartTargets);
    }
  }

  analyze() {
    const result = { concerns: [], metrics: {} };

    if (this.diabeticMode) {
      const diabeticAnalysis = this.diabeticConverter.analyze();
      result.metrics.carbs = diabeticAnalysis;
      if (diabeticAnalysis.currentNetCarbs > 50) {
        result.concerns.push('high_carbs');
      }
    }

    if (this.heartSmartMode) {
      const heartAnalysis = this.heartSmartConverter.analyze();
      result.metrics.heart = heartAnalysis;
      result.concerns.push(...heartAnalysis.concerns);
    }

    return result;
  }

  // Handle conflicts between modes
  resolveConflicts(substitutions) {
    // Example: Diabetic suggests almond flour (high fat)
    //          Heart-smart concerned about fat
    // Resolution: Use almond flour but reduce other fats in recipe

    const conflicts = [];
    // Check if diabetic sub increases sat fat
    // Check if heart-smart sub increases carbs
    // Suggest balanced alternatives

    return { substitutions, conflicts, resolutions };
  }

  generateHealthyRecipe() {
    // Apply both converters, resolve conflicts, return unified result
    return {
      recipe: this.finalRecipe,
      diabeticImprovements: {...},
      heartSmartImprovements: {...},
      conflictsResolved: [...],
      overallHealthScore: this.calculateHealthScore()
    };
  }
}
```

**Phase 4: UI Integration**

```html
<div class="health-converter-panel">
  <h3>Make This Recipe Healthier</h3>

  <div class="converter-options">
    <label>
      <input type="checkbox" id="diabetic-mode"> Diabetic-Friendly
      <span class="target">(<50g carbs)</span>
    </label>
    <label>
      <input type="checkbox" id="heart-smart-mode"> Heart-Smart
      <span class="target">(<600mg sodium, <5g sat fat)</span>
    </label>
  </div>

  <div class="health-metrics">
    <div class="metric sodium">
      <span class="label">Sodium</span>
      <span class="original">1,240mg</span>
      <span class="arrow">→</span>
      <span class="converted">380mg</span>
      <span class="badge good">-69%</span>
    </div>
    <div class="metric carbs">
      <span class="label">Net Carbs</span>
      <span class="original">62g</span>
      <span class="arrow">→</span>
      <span class="converted">14g</span>
      <span class="badge good">-77%</span>
    </div>
    <!-- More metrics -->
  </div>

  <div class="substitution-list">
    <!-- Interactive substitution cards -->
  </div>

  <div class="flavor-enhancements">
    <h4>Flavor Boosters (to compensate for reduced salt)</h4>
    <ul>
      <li>+ 1 tbsp lemon juice</li>
      <li>+ 1/2 tsp cracked black pepper</li>
      <li>+ Fresh herbs: basil, parsley</li>
    </ul>
  </div>
</div>
```

#### AHA-Compliant Presets

```javascript
const HEALTH_PRESETS = {
  'aha-recommended': {
    sodium: 600,      // Per serving (2300mg/day ÷ ~4 meals)
    satFat: 5,        // ~13g/day for 2000 cal
    cholesterol: 100, // 300mg/day ÷ 3 meals
    fiber: 7,         // 25-30g/day
    addedSugar: 6     // 25g/day ÷ ~4 meals
  },
  'dash-diet': {
    sodium: 575,      // Stricter (2300mg max, ideally 1500mg)
    satFat: 4,
    fiber: 8,
    potassium: 1200   // High potassium emphasized
  },
  'mediterranean': {
    sodium: 600,
    satFat: 6,        // More olive oil allowed
    omega3: 1,        // Minimum omega-3 per serving
    fiber: 8
  }
};
```

#### Research Required

- [ ] Complete sodium content database for common ingredients
- [ ] Saturated fat database with cooking method variations
- [ ] Herb/spice flavor pairing research
- [ ] How salt reduction affects food safety (curing, preservation)
- [ ] Interaction effects (reducing salt + reducing fat = double flavor loss)
- [ ] Regional herb blends for different cuisines

#### Success Metrics

- [ ] 85%+ of recipes convertible to <600mg sodium
- [ ] User flavor satisfaction >3.5/5 after conversion
- [ ] Combined diabetic+heart-smart possible for 70%+ of recipes
- [ ] Clear conflict resolution when modes compete

#### Dependencies

- Nutrition estimation tool
- Diabetic converter (for combined mode)
- Ingredient parser
- Herb/spice flavor database

---

---

## CRITICAL: Health Safeguards System

**Status:** ✅ COMPLETE
**Added:** 2026-01-23
**Completed:** 2026-01-28
**Priority:** HIGHEST - User Safety

A comprehensive health safeguards system that warns users about dangerous food interactions with medications, medical conditions, and allergens.

### Implementation Complete

The Health Safeguards System is now fully functional:

- **Data:** `data/health-considerations.json` - 6,369 flagged ingredients across 28 concern categories
- **JavaScript:** `loadHealthConsiderations()`, `analyzeRecipeHealth()`, `renderHealthPanel()` in script.js
- **CSS:** Full styling for collapsible panel with severity-based color coding
- **Integration:** Automatically displays on recipe pages for any recipe with flagged ingredients

**Features:**
- Collapsible "Health Considerations" panel (closed by default)
- Color-coded severity levels: critical (red), high (orange), allergen (yellow), moderate (blue), info (gray)
- Drug-food interaction warnings (MAOI/tyramine, warfarin/vitamin K, grapefruit/CYP3A4, etc.)
- Top 9 allergen detection
- Kidney disease considerations (phosphorus, potassium, sodium)
- Medical disclaimer included

---

### Reference Documentation (Research Notes)

### Drug-Food Interactions (Life-Threatening)

#### 1. Warfarin (Blood Thinners) + Vitamin K

**Risk Level: CRITICAL**
**Consequence:** Uncontrolled bleeding or dangerous clots

| Vitamin K Foods (CONSISTENT intake required) | Action |
|---------------------------------------------|--------|
| Kale, spinach, collard greens, Swiss chard | Maintain consistent amounts, don't suddenly increase/decrease |
| Broccoli, Brussels sprouts, asparagus | Same serving size week-to-week |
| Green tea, matcha | Limit or maintain consistency |
| Liver (beef, chicken) | Very high Vitamin K, avoid |
| Mayonnaise, canola oil, soybean oil | Moderate Vitamin K |

**Warning Text:** "You've indicated you take blood thinners (warfarin). This recipe contains [X]g of Vitamin K from [ingredients]. Maintain consistent Vitamin K intake - sudden changes can affect your medication's effectiveness. Consult your doctor."

**Foods that INCREASE warfarin effect (bleeding risk):**
- Cranberry juice, pomegranate juice
- Grapefruit and grapefruit juice
- Mango, papaya
- Fish oil supplements
- Alcohol (large amounts)

#### 2. MAOIs (Antidepressants) + Tyramine

**Risk Level: CRITICAL - Can be fatal**
**Consequence:** Hypertensive crisis (stroke, death)

MAOIs include: phenelzine (Nardil), tranylcypromine (Parnate), isocarboxazid (Marplan), selegiline (Emsam patch)

| HIGH-TYRAMINE FOODS TO AVOID | Tyramine Content |
|-----------------------------|------------------|
| Aged cheeses (cheddar, Parmesan, blue cheese, Gouda) | Very High |
| Cured meats (salami, pepperoni, summer sausage) | Very High |
| Fermented foods (sauerkraut, kimchi, miso, soy sauce) | High |
| Draft/unpasteurized beer, red wine | High |
| Smoked/pickled fish | High |
| Overripe bananas, avocados | Moderate-High |
| Broad beans (fava beans) | High |
| Yeast extracts (Marmite, Vegemite) | Very High |

**SAFE alternatives:**
- Fresh cheeses (cream cheese, cottage cheese, ricotta)
- Fresh meats (not aged/cured)
- White wine, bottled beer (in moderation)
- Fresh fruits and vegetables

**Warning Text:** "⚠️ DANGER: You've indicated you take an MAOI antidepressant. This recipe contains [aged cheese/cured meat/fermented ingredient] which is HIGH in tyramine. Consuming this could cause a hypertensive crisis (dangerous blood pressure spike). This interaction can be FATAL. Please choose a different recipe or substitute these ingredients."

**Note:** Tyramine restriction must continue 2-3 weeks AFTER stopping MAOIs.

#### 3. Grapefruit + Multiple Medications

**Risk Level: HIGH**
**Consequence:** Medication overdose or reduced effectiveness

Grapefruit inhibits CYP3A4 enzyme, affecting 85+ medications:

| Medication Class | Effect of Grapefruit |
|-----------------|----------------------|
| Statins (atorvastatin, simvastatin) | Increases drug levels → muscle damage |
| Calcium channel blockers (amlodipine, felodipine) | Increases drug levels → low blood pressure |
| Immunosuppressants (cyclosporine, tacrolimus) | Increases toxicity |
| Anti-anxiety (buspirone, diazepam) | Increased sedation |
| Erectile dysfunction (sildenafil) | Dangerous blood pressure drop |
| Some cancer drugs | Altered effectiveness |

**Also avoid:** Pomelo, Seville oranges, tangelos (same compounds)

**Warning Text:** "This recipe contains grapefruit/pomelo/Seville orange. Grapefruit interacts with many medications including [common examples]. If you take prescription medications, consult your pharmacist before consuming grapefruit."

#### 4. ACE Inhibitors + Potassium-Rich Foods

**Risk Level: HIGH**
**Consequence:** Hyperkalemia (dangerous heart rhythm)

ACE inhibitors (lisinopril, enalapril, etc.) and ARBs cause potassium retention.

| High-Potassium Foods to Moderate | Potassium (mg) |
|----------------------------------|----------------|
| Baked potato with skin | 926mg |
| Sweet potato | 542mg |
| Banana | 422mg |
| Orange juice (1 cup) | 496mg |
| Spinach (1 cup cooked) | 839mg |
| Tomato sauce (1 cup) | 728mg |
| Salt substitutes (potassium chloride) | VERY HIGH - AVOID |

**Warning Text:** "You've indicated you take ACE inhibitors or ARBs. This recipe is high in potassium ([X]mg per serving). Your medications cause potassium retention. Monitor your potassium intake and discuss with your doctor."

### Kidney Disease (CKD) Dietary Restrictions

**Risk Level: HIGH**
**Consequence:** Dialysis complications, heart problems, bone disease

| CKD Stage | Sodium | Potassium | Phosphorus | Protein |
|-----------|--------|-----------|------------|---------|
| 1-2 | <2300mg/day | Usually OK | Usually OK | Normal |
| 3 | <2300mg/day | May need limit | Limit if elevated | Moderate |
| 4 | <2000mg/day | <2000-3000mg/day | <800-1000mg/day | Limit |
| 5/Dialysis | <2000mg/day | <2000mg/day | <800mg/day | Higher (dialysis) |

**High-Phosphorus Foods to Flag:**
- Dairy products (milk, cheese, yogurt)
- Nuts and seeds
- Whole grains (brown rice, whole wheat bread)
- Cola drinks (phosphoric acid)
- Processed foods with phosphate additives (PHOS in ingredients)
- Organ meats

**Warning Text:** "You've indicated you have kidney disease. This recipe contains [X]mg phosphorus and [X]mg potassium per serving. Recommended limits for your stage: phosphorus <[X]mg, potassium <[X]mg. Consult your renal dietitian."

### Immunocompromised Food Safety

**Applies to:** Pregnant women, chemotherapy patients, HIV/AIDS, transplant recipients, elderly (65+)

**Risk Level: HIGH**
**Consequence:** Listeriosis, salmonella, severe foodborne illness

| AVOID These Foods | Risk | Safe Alternative |
|-------------------|------|------------------|
| Soft cheeses (brie, feta, queso fresco) | Listeria | Hard cheeses, pasteurized options |
| Deli meats, hot dogs (unless heated to steaming) | Listeria | Heat until steaming (165°F) |
| Raw/undercooked eggs | Salmonella | Cook until firm, use pasteurized eggs |
| Raw sprouts (alfalfa, bean) | E. coli, Salmonella | Cooked sprouts only |
| Unpasteurized juice/cider | E. coli | Pasteurized only |
| Raw fish (sushi, sashimi) | Parasites, bacteria | Fully cooked fish |
| Smoked seafood (unless in cooked dish) | Listeria | Canned or fully cooked |
| Raw cookie dough/batter | Salmonella, E. coli | Bake fully |

**Pregnancy-Specific:**
- **Listeriosis risk:** 10x higher in pregnancy
- **Mercury in fish:** Limit albacore tuna, avoid shark/swordfish/king mackerel
- **Caffeine:** Limit to 200mg/day

**Warning Text:** "⚠️ IMMUNOCOMPROMISED WARNING: This recipe contains [raw eggs/unpasteurized cheese/deli meat]. For pregnant women, chemotherapy patients, or those with weakened immune systems, these ingredients carry serious infection risks including Listeria. Please cook thoroughly or substitute with safer alternatives."

### Allergen Cross-Contamination Warnings

**Top 9 Allergens (US):**
1. Milk
2. Eggs
3. Fish
4. Shellfish
5. Tree nuts
6. Peanuts
7. Wheat
8. Soybeans
9. Sesame

**Hidden Allergens to Flag:**
| Allergen | Hidden In |
|----------|-----------|
| Milk | Casein, whey, lactose, ghee, some margarines |
| Eggs | Mayonnaise, meringue, some pasta, marshmallows |
| Wheat | Soy sauce, some stocks, breading, communion wafers |
| Soy | Vegetable oil, lecithin, tofu, miso, edamame |
| Tree nuts | Pesto (pine nuts), marzipan, nut oils |
| Peanuts | Some Asian sauces, some candies, "arachis oil" |
| Shellfish | Fish sauce, some Caesar dressings, glucosamine |
| Sesame | Tahini, hummus, some breads, "benne seeds" |

**Cross-Contamination Warnings:**
- Shared fryers (fish/shellfish with other foods)
- Shared cutting boards/utensils
- "May contain" labeling
- Restaurant/bakery cross-contact risks

**Warning Text:** "You've indicated allergies to [X]. This recipe contains [ingredient] which is/contains [allergen]. Additionally, [related ingredient] may contain traces of [allergen]. Please verify all ingredients and consider cross-contamination risks."

### Implementation: Collapsible Health Considerations Section

**NO USER ACCOUNTS REQUIRED** - Instead, display a collapsible "Health Considerations" section on any recipe that contains flagged ingredients. The section starts **closed by default** and users can expand it to view relevant warnings.

#### Data File Created

✅ **`data/health-considerations.json`** - Comprehensive database with:
- **6,369 flagged ingredients** (of 10,980 total)
- **28 health concern categories**
- Severity levels: `critical`, `high`, `moderate`, `allergen`, `info`

**Categories include:**
| Category | Ingredients Flagged | Severity |
|----------|---------------------|----------|
| High Phosphorus (Kidney Disease) | 1,464 | moderate |
| Milk/Dairy Allergen | 1,332 | allergen |
| High FODMAP Content | 1,325 | info |
| Calcium/Antibiotic Interaction | 1,106 | moderate |
| Vitamin K (Warfarin) | 951 | high |
| High Histamine Content | 920 | info |
| Wheat/Gluten Allergen | 875 | allergen |
| High Potassium (ACE Inhibitors) | 796 | moderate |
| High Sodium (Kidney/Heart) | 778 | moderate |
| Tyramine (MAOI) | 708 | **critical** |
| High Glycemic Index | 677 | moderate |
| Egg Allergen | 266 | allergen |
| Goitrogen (Thyroid) | 248 | info |
| Contains Alcohol | 232 | info |
| Contains Caffeine | 206 | info |
| Tree Nut Allergen | 180 | allergen |
| Fish Allergen | 164 | allergen |
| Shellfish Allergen | 69 | allergen |
| Peanut Allergen | 43 | allergen |
| Unpasteurized (Immunocompromised) | 40 | high |
| Soy Allergen | 39 | allergen |
| Sesame Allergen | 37 | allergen |
| Raw Seafood (Immunocompromised) | 13 | high |
| Raw Sprouts (Immunocompromised) | 11 | moderate |
| Grapefruit (CYP3A4) | 9 | high |
| Raw Eggs (Immunocompromised) | 8 | high |
| Raw Meat (Immunocompromised) | 1 | high |

#### UI Design: Collapsible Health Considerations

```html
<!-- On recipe.html, after ingredients section -->
<details class="health-considerations" id="health-panel">
  <summary class="health-header">
    <span class="health-icon">⚕️</span>
    <span class="health-title">Health Considerations</span>
    <span class="health-count">(5 items)</span>
    <span class="chevron">▶</span>
  </summary>

  <div class="health-content">
    <!-- Critical warnings first (red) -->
    <div class="health-warning critical">
      <h4>⚠️ MAOI Drug Interaction - CRITICAL</h4>
      <p><strong>Ingredients:</strong> aged parmesan cheese, soy sauce</p>
      <p>CRITICAL: Tyramine can cause dangerous blood pressure spikes with MAOI medications. This interaction can be fatal.</p>
      <p><em>Medications affected:</em> phenelzine (Nardil), tranylcypromine (Parnate)</p>
    </div>

    <!-- High severity (orange) -->
    <div class="health-warning high">
      <h4>Vitamin K Content (Warfarin Interaction)</h4>
      <p><strong>Ingredients:</strong> spinach, broccoli, olive oil</p>
      <p>High vitamin K content may reduce warfarin effectiveness. Maintain consistent intake if on blood thinners.</p>
    </div>

    <!-- Allergen warnings (yellow) -->
    <div class="health-warning allergen">
      <h4>Contains Milk/Dairy</h4>
      <p><strong>Ingredients:</strong> butter, parmesan cheese, cream</p>
      <p>Contains milk or dairy products. One of the top 9 allergens.</p>
    </div>

    <!-- Moderate/Info (blue/gray) -->
    <div class="health-warning moderate">
      <h4>High Sodium (Kidney/Heart Disease)</h4>
      <p><strong>Ingredients:</strong> soy sauce, parmesan cheese</p>
      <p>May contain high sodium. People with kidney or heart disease should limit sodium.</p>
    </div>
  </div>
</details>
```

#### CSS Styling

```css
/* Health Considerations Panel */
.health-considerations {
  margin: 1rem 0;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: #fafafa;
}

.health-considerations[open] .chevron {
  transform: rotate(90deg);
}

.health-header {
  padding: 0.75rem 1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  user-select: none;
}

.health-header:hover {
  background: #f0f0f0;
}

.health-count {
  color: #666;
  font-weight: normal;
  font-size: 0.9em;
}

.chevron {
  margin-left: auto;
  transition: transform 0.2s;
}

.health-content {
  padding: 0 1rem 1rem;
}

/* Warning severity levels */
.health-warning {
  padding: 0.75rem 1rem;
  margin: 0.5rem 0;
  border-radius: 6px;
  border-left: 4px solid;
}

.health-warning.critical {
  background: #fee2e2;
  border-color: #dc2626;
}

.health-warning.critical h4 {
  color: #dc2626;
}

.health-warning.high {
  background: #ffedd5;
  border-color: #ea580c;
}

.health-warning.high h4 {
  color: #ea580c;
}

.health-warning.allergen {
  background: #fef3c7;
  border-color: #d97706;
}

.health-warning.allergen h4 {
  color: #d97706;
}

.health-warning.moderate {
  background: #dbeafe;
  border-color: #2563eb;
}

.health-warning.moderate h4 {
  color: #2563eb;
}

.health-warning.info {
  background: #f3f4f6;
  border-color: #6b7280;
}

.health-warning.info h4 {
  color: #6b7280;
}

.health-warning h4 {
  margin: 0 0 0.5rem 0;
  font-size: 1rem;
}

.health-warning p {
  margin: 0.25rem 0;
  font-size: 0.9rem;
}
```

#### JavaScript Implementation

```javascript
// Load health considerations database
let healthConsiderations = null;

async function loadHealthConsiderations() {
  if (!healthConsiderations) {
    const response = await fetch('data/health-considerations.json');
    healthConsiderations = await response.json();
  }
  return healthConsiderations;
}

// Analyze recipe ingredients for health concerns
async function analyzeRecipeHealth(recipe) {
  const db = await loadHealthConsiderations();
  const warnings = new Map(); // concernId -> { concern, ingredients: [] }

  for (const ingredient of recipe.ingredients) {
    const ingText = ingredient.item?.toLowerCase() || ingredient.toLowerCase();

    // Check if this ingredient has any health concerns
    const concerns = db.ingredients[ingText];
    if (concerns) {
      for (const concernId of concerns) {
        if (!warnings.has(concernId)) {
          warnings.set(concernId, {
            concern: db.concerns[concernId],
            concernId: concernId,
            ingredients: []
          });
        }
        warnings.get(concernId).ingredients.push(ingText);
      }
    }
  }

  // Sort by severity: critical > high > allergen > moderate > info
  const severityOrder = { critical: 0, high: 1, allergen: 2, moderate: 3, info: 4 };
  return Array.from(warnings.values())
    .sort((a, b) => severityOrder[a.concern.severity] - severityOrder[b.concern.severity]);
}

// Render health considerations panel
function renderHealthPanel(warnings, container) {
  if (warnings.length === 0) {
    container.style.display = 'none';
    return;
  }

  const details = document.createElement('details');
  details.className = 'health-considerations';

  // Summary (always visible)
  const summary = document.createElement('summary');
  summary.className = 'health-header';
  summary.innerHTML = `
    <span class="health-icon">⚕️</span>
    <span class="health-title">Health Considerations</span>
    <span class="health-count">(${warnings.length} items)</span>
    <span class="chevron">▶</span>
  `;
  details.appendChild(summary);

  // Content (hidden by default)
  const content = document.createElement('div');
  content.className = 'health-content';

  for (const warning of warnings) {
    const div = document.createElement('div');
    div.className = `health-warning ${warning.concern.severity}`;

    let html = `<h4>${warning.concern.title}</h4>`;
    html += `<p><strong>Ingredients:</strong> ${warning.ingredients.join(', ')}</p>`;
    html += `<p>${warning.concern.description}</p>`;

    if (warning.concern.medications && warning.concern.medications.length > 0) {
      html += `<p><em>Medications affected:</em> ${warning.concern.medications.join(', ')}</p>`;
    }

    div.innerHTML = html;
    content.appendChild(div);
  }

  details.appendChild(content);
  container.appendChild(details);
}

// Usage in recipe page
async function displayRecipe(recipe) {
  // ... existing recipe display code ...

  // Add health considerations panel
  const healthContainer = document.getElementById('health-container');
  const warnings = await analyzeRecipeHealth(recipe);
  renderHealthPanel(warnings, healthContainer);
}
```

#### Integration Points

1. **recipe.html**: Add `<div id="health-container"></div>` after ingredients
2. **script.js**: Call `analyzeRecipeHealth()` when displaying recipe
3. **styles.css**: Add health panel CSS
4. **Service Worker**: Cache `health-considerations.json` for offline use

#### Data Structure: health-considerations.json

```json
{
  "meta": {
    "version": "1.0.0",
    "description": "Health considerations for recipe ingredients",
    "total_flagged_ingredients": 6369,
    "concern_categories": 28
  },
  "concerns": {
    "maoi_tyramine": {
      "title": "Tyramine Content (MAOI Interaction)",
      "severity": "critical",
      "description": "CRITICAL: Tyramine can cause dangerous blood pressure spikes...",
      "medications": ["phenelzine (Nardil)", "tranylcypromine (Parnate)"]
    },
    "allergen_milk": {
      "title": "Milk/Dairy Allergen",
      "severity": "allergen",
      "description": "Contains milk or dairy products. One of the top 9 allergens.",
      "medications": []
    }
    // ... 26 more categories
  },
  "ingredients": {
    "aged parmesan cheese": ["maoi_tyramine", "allergen_milk", "ckd_high_phosphorus"],
    "spinach": ["warfarin_vitamin_k", "ace_potassium", "ckd_high_potassium"],
    "peanut butter": ["allergen_peanuts", "ckd_high_phosphorus"]
    // ... 6,366 more ingredients
  }
}
```

### Disclaimer Requirements

**MANDATORY disclaimer in Health Considerations panel:**

```html
<p class="health-disclaimer">
  <strong>Medical Disclaimer:</strong> This information is for general
  awareness only and is NOT medical advice. Always consult your doctor,
  pharmacist, or registered dietitian before making dietary changes,
  especially if you have medical conditions or take medications.
  Food-drug interactions can be serious or life-threatening.
</p>
```

**Display at bottom of Health Considerations panel when expanded.**

### Research Sources

- [Pharmacy Times: 5 Dangerous Food-Drug Interactions](https://www.pharmacytimes.com/view/5-dangerous-food-drug-interactions)
- [AHA: Medication Interactions with Food](https://www.heart.org/en/health-topics/consumer-healthcare/medication-information/medication-interactions-food-supplements-and-other-drugs)
- [NIH: Warfarin Food Interactions](https://www.ncbi.nlm.nih.gov/books/NBK563197/)
- [NIDDK: Healthy Eating for CKD](https://www.niddk.nih.gov/health-information/kidney-disease/chronic-kidney-disease-ckd/healthy-eating-adults-chronic-kidney-disease)
- [CDC: Food Safety for Pregnant Women](https://www.cdc.gov/food-safety/foods/pregnant-women.html)
- [FDA: Listeria Safety](https://www.fda.gov/food/health-educators/listeria-food-safety-moms-be)
- [Memorial Sloan Kettering: Neutropenic Diet](https://www.mskcc.org/experience/patient-support/nutrition-cancer/diet-plans-cancer/neutropenic-diet)

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

## In Progress: Image Processing

**Status:** Partially Complete (2026-01-25)

### Current State

| Collection | Total | Validated | Oversized | Processed Copies |
|------------|-------|-----------|-----------|------------------|
| grandma | 494 | 494 | 0 | N/A (all <2000px) |
| reference (data/all/) | 906 | 152 | 754 | 754 in `data/all/processed/` |
| mommom | 104 | 0 | 104 | **Remote** (MomsRecipes repo) |

**Note:** The 104 mommom images are tracked in the manifest but exist in the remote MomsRecipes repository, not locally. The `process_images.py` script creates resized copies in a `processed/` subfolder while preserving originals.

### Next Steps

1. **Cross-Repository Duplicate Check**
   - Check MomsRecipes, Grannysrecipes, Allrecipes for duplicate recipes
   - Not just local JSON - check actual remote repositories
   - Variants are OK, but true duplicates should be consolidated

2. **Image Transcription**
   - 754 reference images now have AI-safe processed versions
   - Use `data/all/processed/*.jpeg` for transcription
   - Remember: MAX 100 images per API request

---

## Completed Tasks

| Task | Completed | Notes |
|------|-----------|-------|
| **Implement Health Safeguards UI** | 2026-01-28 | Collapsible panel with drug-food interactions, allergens, severity levels |
| Process 754 oversized reference images | 2026-01-25 | Resized to <2000px in data/all/processed/ |
| Add documentation rules to CLAUDE.md | 2026-01-25 | Document everything, 100-image limit, commit/push |
| Create health-considerations.json | 2026-01-23 | 6,369 ingredients flagged across 28 concern categories |
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
