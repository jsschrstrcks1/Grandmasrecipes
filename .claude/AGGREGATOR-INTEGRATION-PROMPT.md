# Milk Substitution Tool Integration for FamilyRecipeHub

> Copy this prompt to the FamilyRecipeHub repository to integrate the Milk Substitution Calculator from Allrecipes.

---

## Overview

The Allrecipes repository contains a Milk Substitution Calculator that allows users to:
1. Switch cheesemaking recipes between cow, goat, and sheep milk
2. Create custom milk blends (percentages or actual volumes like "4 cups goat, 1 gallon cow")
3. Automatically adjust ingredient quantities (milk, rennet, CaCl2)
4. See expected impact on flavor, texture, and yield
5. Handle exotic milks (buffalo, camel, yak, etc.) with substitution recommendations

---

## Files to Copy from Allrecipes

```
Allrecipes/
├── milk-substitution.js          # Core module (~1700 lines)
├── data/milk-substitution.json   # Milk type reference data (~600 lines)
└── styles.css                    # Search for ".milk-" CSS rules (~500 lines)
```

---

## Integration Steps

### 1. Copy Files to Aggregator

```bash
# From FamilyRecipeHub root
cp ../Allrecipes/milk-substitution.js assets/js/
cp ../Allrecipes/data/milk-substitution.json data/
# Extract milk substitution CSS rules from styles.css to your stylesheet
```

### 2. Include the Module in HTML

```html
<!-- Before your main script -->
<script src="assets/js/milk-substitution.js"></script>
<script src="assets/js/main.js"></script>
```

### 3. Initialize on Page Load

```javascript
async function init() {
  // Load milk substitution data
  if (typeof MilkSubstitution !== 'undefined') {
    await MilkSubstitution.loadData();
    console.log('Milk substitution tool ready');
  }

  // ... rest of your initialization
}

document.addEventListener('DOMContentLoaded', init);
```

### 4. Render Calculator for Cheese Recipes

When displaying a recipe from any collection, check if it's a cheesemaking recipe:

```javascript
function displayRecipe(recipe) {
  // ... render recipe content ...

  // Check if this is a cheesemaking recipe
  if (typeof MilkSubstitution !== 'undefined' && MilkSubstitution.isCheeseRecipe(recipe)) {
    // Create container in your recipe HTML
    const container = document.getElementById('milk-substitution-container');
    if (container) {
      MilkSubstitution.renderMilkSwitcher(recipe, 'milk-substitution-container');
    }
  }
}
```

### 5. Add HTML Container to Recipe Template

```html
<!-- In your recipe detail template -->
<div class="recipe-content">
  <!-- ... other recipe sections ... -->

  <!-- Milk Substitution Calculator (appears only for cheese recipes) -->
  <div id="milk-substitution-container"></div>

  <!-- ... ingredients, instructions, etc. ... -->
</div>
```

### 6. Listen for Substitution Changes

Update the ingredient display when the user changes milk settings:

```javascript
document.addEventListener('milkSubstitutionChanged', (e) => {
  const {
    adjustedIngredients,  // Ready to display
    blendedNutrition,     // Nutrition per cup of blend
    milkRatios,           // { cow: 50, goat: 25, sheep: 25 }
    volumeMode,           // true if user entered volumes
    totalVolumeCups       // Total milk volume
  } = e.detail;

  // Update your ingredients display
  updateIngredientsDisplay(adjustedIngredients);

  // Optionally show nutrition changes
  if (blendedNutrition) {
    updateNutritionDisplay(blendedNutrition);
  }
});

function updateIngredientsDisplay(ingredients) {
  const list = document.getElementById('ingredients-list');
  list.innerHTML = ingredients.map(ing => {
    const adjusted = ing._adjusted ? ' class="adjusted-ingredient"' : '';
    const note = ing._adjustmentNote ? ` <span class="adjustment-note">(${ing._adjustmentNote})</span>` : '';
    return `<li${adjusted}>${ing.quantity} ${ing.unit} ${ing.item}${note}</li>`;
  }).join('');
}
```

### 7. Copy Required CSS

Extract these CSS rule groups from `Allrecipes/styles.css`:

```css
/* Search for and copy all rules starting with: */
.milk-substitution-panel
.milk-sub-*
.milk-blend-*
.milk-ratio-*
.milk-volume-*
.milk-info-*
.milk-nutrition-*
.milk-impact-*
.exotic-milk-*
.mode-btn
.ratio-total*
.volume-total*
.impact-*

/* Also copy the responsive rules */
@media (max-width: 768px) { /* milk-* rules */ }
@media (max-width: 480px) { /* milk-* rules */ }
@media print { .milk-substitution-panel { display: none; } }
```

---

## API Reference

### Detection Functions

```javascript
// Check if recipe is a cheesemaking recipe
MilkSubstitution.isCheeseRecipe(recipe) // → boolean

// Detect what milk type the recipe uses
MilkSubstitution.detectOriginalMilkType(recipe) // → 'cow' | 'goat' | 'sheep' | 'buffalo' | ...

// Check if milk type is available (cow/goat/sheep) vs exotic
MilkSubstitution.isAvailableMilkType('buffalo') // → false
MilkSubstitution.isExoticMilkType('buffalo') // → true
```

### Rendering

```javascript
// Render the full calculator UI
MilkSubstitution.renderMilkSwitcher(recipe, 'container-id')
```

### State Management

```javascript
// Get current blend percentages
MilkSubstitution.getMilkRatios() // → { cow: 50, goat: 25, sheep: 25 }

// Get current volumes (in cups)
MilkSubstitution.getMilkVolumes() // → { cow: 8, goat: 4, sheep: 4 }

// Check current mode
MilkSubstitution.isMixedMode() // → true if using percentage sliders
MilkSubstitution.isVolumeMode() // → true if using volume inputs

// Set milk blend
MilkSubstitution.setSingleMilk('sheep') // 100% sheep
MilkSubstitution.setMilkRatio('goat', 25) // Set goat to 25%, adjusts others
MilkSubstitution.setMilkVolume('cow', 1, 'gallon') // Set cow to 1 gallon
```

### Calculations

```javascript
// Get adjusted ingredients list
MilkSubstitution.getAdjustedIngredients(recipe, multiplier) // → adjusted ingredient array

// Get blended milk properties
MilkSubstitution.getBlendedMilkInfo() // → { fat_percent, protein_percent, cheese_yield_per_gallon_lb, coagulation_speed, flavor_profile, texture_notes }

// Get blended nutrition per cup
MilkSubstitution.getBlendedNutrition() // → { calories, fat_g, protein_g, calcium_mg, ... }

// Get impact assessment
MilkSubstitution.getSubstitutionImpact('cow') // → { flavorChanges, textureChanges, yieldChange, recommendations, ... }
MilkSubstitution.getImpactSummary('cow') // → { summary, flavor, texture, yield, tips, processingNotes }
```

### Volume Utilities

```javascript
// Convert between units
MilkSubstitution.convertToCups(1, 'gallon') // → 16
MilkSubstitution.convertToCups(1, 'quart') // → 4
MilkSubstitution.getTotalVolumeCups() // → total milk entered
```

---

## Event Payload

The `milkSubstitutionChanged` event contains:

```javascript
{
  originalMilkType: "cow",           // What recipe originally used
  milkRatios: { cow: 50, goat: 25, sheep: 25 },
  milkVolumes: { cow: 8, goat: 4, sheep: 4 }, // In cups
  mixedMode: true,                   // Percentage mode active
  volumeMode: false,                 // Volume input mode active
  quantityMultiplier: 1.0,           // Batch size (0.5x, 1x, 2x, etc.)
  totalVolumeCups: 16,               // Total milk volume
  adjustedIngredients: [             // Ready to display
    { item: "milk (50% Cow + 25% Goat + 25% Sheep)", quantity: "1.2", unit: "gallons", _adjusted: true, _adjustmentNote: "..." },
    { item: "liquid rennet", quantity: "1/4", unit: "tsp", _adjusted: true },
    // ...
  ],
  blendedNutrition: { calories: 180, fat_g: 11, protein_g: 10, calcium_mg: 350, ... },
  blendedMilkInfo: { fat_percent: 5.2, protein_percent: 4.1, cheese_yield_per_gallon_lb: 0.4, ... }
}
```

---

## Recipe Detection Requirements

For automatic detection, cheese recipes should have ONE of:

1. **Explicit marker** (recommended):
   ```json
   { "milk_substitutions": { "enabled": true, "original_milk": "cow" } }
   ```

2. **Category**:
   ```json
   { "category": "cheese" }
   ```

3. **Tags**:
   ```json
   { "tags": ["cheesemaking", "cheese", "fresh-cheese", "aged-cheese", "curds", "whey"] }
   ```

4. **Title** containing cheese variety names + milk ingredient

5. **Ingredients** with rennet + milk

---

## Collection Normalization

When aggregating from multiple family recipe repositories, normalize the `milk_substitutions` field:

```javascript
function normalizeRecipe(recipe, sourceRepo) {
  // Ensure milk_substitutions field exists for cheese recipes
  if (MilkSubstitution.isCheeseRecipe(recipe) && !recipe.milk_substitutions) {
    recipe.milk_substitutions = {
      enabled: true,
      original_milk: MilkSubstitution.detectOriginalMilkType(recipe),
      supported_types: ['cow', 'goat', 'sheep']
    };
  }
  return recipe;
}
```

---

## Styling / Theming

The tool uses CSS custom properties. Override these to match your theme:

```css
:root {
  --color-warm-white: #faf8f5;
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --font-heading: 'Your Heading Font', serif;
}
```

Or override specific colors:
- **Blue theme** (main panel): `#1565c0`, `#2196f3`, `#64b5f6`, `#bbdefb`, `#e3f2fd`
- **Green theme** (impact panel): `#2e7d32`, `#4caf50`, `#81c784`, `#c8e6c9`, `#e8f5e9`
- **Purple theme** (nutrition): `#7b1fa2`, `#ce93d8`, `#e1bee7`, `#f3e5f5`
- **Yellow theme** (warnings): `#ff9800`, `#ffc107`, `#ffecb3`, `#fff8e1`

---

## Troubleshooting

**Calculator not appearing:**
- Check browser console for errors loading `milk-substitution.json`
- Verify `MilkSubstitution.isCheeseRecipe(recipe)` returns `true`
- Ensure container element exists: `<div id="milk-substitution-container"></div>`

**Ingredients not updating:**
- Verify event listener is attached: `document.addEventListener('milkSubstitutionChanged', ...)`
- Check that `adjustedIngredients` array contains items

**Wrong milk type detected:**
- Add explicit `milk_substitutions.original_milk` to recipe
- Ensure milk ingredient includes type: "goat milk" not just "milk"
