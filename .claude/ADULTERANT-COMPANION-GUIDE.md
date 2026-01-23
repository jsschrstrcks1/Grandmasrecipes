# Adulterant Companion Tool Integration Guide

> Documentation for integrating the Cheese Adulterant (Additive) system from Allrecipes into the family recipe hub.

---

## Overview

The Allrecipes repository contains an **Adulterant Companion** system that allows cheesemakers to:

1. Add flavorings, herbs, spices, and other additives to cheese recipes
2. Calculate proper quantities based on milk type and batch size
3. Get safety warnings for dangerous additives (extreme heat peppers)
4. See compatibility with different cheese styles
5. Integrate with the Milk Substitution tool for quantity adjustments

**Note:** Despite the name "adulterant," these are legitimate cheese additives (herbs, spices, etc.), not contaminants.

---

## Files on Allrecipes

```
Allrecipes/
├── adulterant-companion.js     # Core module (~24KB, 23 public functions)
├── cheese-builder.html         # Interactive cheese builder with adulterant panel
├── cheese-builder.js           # Cheese builder logic (~84KB)
└── data/
    └── adulterants.json        # 156 additives across 9 categories
```

---

## Adulterant Categories (9 Total)

| Category | Icon | Examples | Typical Quantity Range |
|----------|------|----------|------------------------|
| Hot Peppers & Chili Powders | 🌶️ | Crushed red pepper, cayenne, ghost pepper, Carolina Reaper, Pepper X | 0.03-2 tsp/gallon |
| Dried Herbs | 🌿 | Oregano, thyme, rosemary, basil, dill, sage, tarragon | 0.5-2 tsp/gallon |
| Spices | 🧂 | Black pepper, cumin, caraway, fennel, coriander | 0.25-1 tsp/gallon |
| Indian Spices | 🍛 | Turmeric, fenugreek, cardamom, mustard seeds | 0.25-1 tsp/gallon |
| Alliums | 🧄 | Garlic powder, roasted garlic, onion powder, shallot powder | 0.5-1.5 tsp/gallon |
| Alcohol & Washes | 🍷 | Red wine, beer, whiskey, calvados, port | Varies by application |
| Dried Fruits | 🍇 | Cranberries, apricots, figs, dates | 2-4 tbsp/gallon |
| Nuts & Seeds | 🥜 | Walnuts, almonds, hazelnuts, pumpkin seeds | 2-4 tbsp/gallon |
| Other | ✨ | Truffle oil, honey, liquid smoke, ash, saffron, nettle | Varies widely |

---

## Safety Levels

The system uses four warning levels:

| Level | Icon | Meaning | Example |
|-------|------|---------|---------|
| **Info** | ℹ️ | Standard usage guidance | Most herbs and spices |
| **Caution** | ⚠️ | Use carefully, may overpower | Strong spices like cumin |
| **Warning** | ⚡ | Can cause adverse reactions | Hot peppers (cayenne+) |
| **Danger** | ☠️ | Extreme care required | Ghost pepper, Carolina Reaper, Pepper X |

### Extreme Heat Peppers (Danger Level)

| Pepper | Intensity | Base Qty/Gallon | Max Qty/Gallon |
|--------|-----------|-----------------|----------------|
| Ghost Pepper | E6 | 0.125 tsp | 0.5 tsp |
| Carolina Reaper | E6 | 0.0625 tsp | 0.25 tsp |
| Pepper X | E6 | 0.03125 tsp | 0.125 tsp |

---

## Prohibited Adulterants

These are **NEVER** safe for cheesemaking due to botulism or spoilage risk:

| Prohibited Item | Reason |
|-----------------|--------|
| Fresh garlic | Botulism risk (Clostridium botulinum) |
| Fresh onion | Moisture promotes bacterial growth |
| Fresh herbs | Same moisture/bacteria issues |
| Vinegar-based hot sauce | Disrupts acid balance, inconsistent results |
| Asafoetida | Overpowering, unpredictable fermentation |
| Pre-mixed garam masala | Unknown additives, inconsistent |

**Safe Alternative:** Use dried/powdered versions of garlic, onion, and herbs.

---

## Addition Stages

Adulterants can be added at different stages of cheesemaking:

| Stage | When | Best For |
|-------|------|----------|
| Cold Infuse | Before heating milk | Delicate flavors (saffron, truffle) |
| Milk Preheat | During initial heating | Herbs, mild spices |
| Curd Mill | After cutting curds | Most solid additions |
| Mold Layer | Layering in mold | Visual appeal, layered flavors |
| Post-Press | After pressing | Surface treatments |
| Brine | During brining | Salt-compatible additions |
| Rind Rub | On exterior | Herbs, spices, ash |
| Aging Surface | During affinage | Washes, oils |
| Finish/Serving | Before serving | Fresh herbs, oils, honey |

---

## Milk Type Adjustments

Quantities automatically adjust based on milk type:

| Milk Type | Adjustment | Reason |
|-----------|------------|--------|
| Cow | Baseline (1.0x) | Standard reference |
| Goat | 0.9-0.95x (slight reduction) | Stronger inherent flavor |
| Sheep | 1.3-1.4x (increase) | Higher fat content absorbs more |
| Buffalo | 1.2-1.3x (increase) | Rich milk needs more flavoring |

---

## API Reference

### Data Operations

```javascript
// Load adulterant data (required first)
await AdulterantCompanion.loadData();

// Get all adulterants
AdulterantCompanion.getAllAdulterants(); // → array of 156 adulterants

// Get by category
AdulterantCompanion.getByCategory('herbs'); // → array

// Get specific adulterant
AdulterantCompanion.getAdulterant('garlic-powder'); // → object

// Get prohibited list
AdulterantCompanion.getProhibited(); // → array of unsafe items
```

### Compatibility Checking

```javascript
// Check if adulterant works with cheese style
AdulterantCompanion.isCompatible('truffle-oil', 'brie'); // → true
AdulterantCompanion.isIncompatible('carolina-reaper', 'fresh-mozzarella'); // → true

// Get compatible adulterants for a cheese style
AdulterantCompanion.getCompatibleAdulterants('cheddar'); // → filtered array

// Detect cheese style from recipe
AdulterantCompanion.detectCheeseStyle(recipe); // → 'cheddar' | 'mozzarella' | ...
```

### Quantity Calculations

```javascript
// Get milk-adjusted quantity
AdulterantCompanion.getMilkAdjustment('sheep'); // → 1.35

// Calculate adjusted quantity for milk type and batch size
AdulterantCompanion.calculateAdjustedQuantity(
  adulterant,
  milkType,    // 'cow' | 'goat' | 'sheep'
  batchMultiplier  // 0.5, 1, 2, etc.
); // → { quantity: '0.75', unit: 'tsp' }

// Format for display
AdulterantCompanion.formatQuantity(0.75, 'tsp'); // → '3/4 tsp'
```

### Safety & Warnings

```javascript
// Get warnings for an adulterant
AdulterantCompanion.getWarnings('ghost-pepper');
// → [{ level: 'danger', message: 'Extreme heat...' }]

// Get all warnings for current selections
AdulterantCompanion.getAllWarnings(); // → array of warning objects

// Check for interactions between selected adulterants
AdulterantCompanion.checkInteractions();
// → [{ type: 'conflict', items: [...], message: '...' }]
```

### Selection Management

```javascript
// Add adulterant to selection
AdulterantCompanion.addAdulterant('rosemary', { quantity: 1, unit: 'tsp' });

// Remove from selection
AdulterantCompanion.removeAdulterant('rosemary');

// Update quantity
AdulterantCompanion.updateQuantity('rosemary', 1.5, 'tsp');

// Get current selections
AdulterantCompanion.getSelections(); // → array of selected adulterants

// Clear all
AdulterantCompanion.clearSelections();
```

### Recipe Integration

```javascript
// Set the current recipe context
AdulterantCompanion.setRecipe(recipe);

// Set milk type (usually via event from MilkSubstitution)
AdulterantCompanion.setMilkType('goat');

// Generate injection steps for recipe workflow
AdulterantCompanion.generateInjectionSteps();
// → [{ stage: 'curd_mill', adulterants: [...], instructions: '...' }]
```

### UI Rendering

```javascript
// Render the adulterant panel in a container
AdulterantCompanion.renderPanel('adulterant-container');
```

---

## Event Integration

### Listening to Milk Substitution Changes

The Adulterant Companion listens for milk type changes:

```javascript
document.addEventListener('milkSubstitutionChanged', (e) => {
  const { milkRatios } = e.detail;
  // AdulterantCompanion automatically adjusts quantities
});
```

### Adulterant Selection Events

```javascript
document.addEventListener('adulterantSelectionChanged', (e) => {
  const { selections, warnings, injectionSteps } = e.detail;
  // Update UI accordingly
});
```

---

## Integration Steps for Grandmasrecipes

### 1. Copy Files (Optional - Can Link Instead)

```bash
# If hosting locally:
cp ../Allrecipes/adulterant-companion.js assets/js/
cp ../Allrecipes/data/adulterants.json data/

# Or link to Allrecipes hosted version (recommended)
```

### 2. Add Script Reference

```html
<!-- In recipe.html, after milk-substitution.js -->
<script src="https://jsschrstrcks1.github.io/Allrecipes/adulterant-companion.js"></script>
```

### 3. Add Container to Recipe Template

```html
<!-- After milk-substitution-container -->
<div id="adulterant-container"></div>
```

### 4. Initialize for Cheese Recipes

```javascript
async function displayRecipe(recipe) {
  // ... render recipe ...

  if (MilkSubstitution.isCheeseRecipe(recipe)) {
    // Render milk substitution panel
    MilkSubstitution.renderMilkSwitcher(recipe, 'milk-substitution-container');

    // Render adulterant panel
    if (typeof AdulterantCompanion !== 'undefined') {
      await AdulterantCompanion.loadData();
      AdulterantCompanion.setRecipe(recipe);
      AdulterantCompanion.renderPanel('adulterant-container');
    }
  }
}
```

---

## Cheese Builder Page

The full cheese builder is available at:
**https://jsschrstrcks1.github.io/Allrecipes/cheese-builder.html**

This page provides:
- Interactive cheese recipe creation wizard
- Full adulterant selection panel
- Milk type switching with quantity adjustments
- Recipe JSON export (copies to clipboard)
- Integration with the full 2,013 cheese recipes

### Linking from Grandmasrecipes

Add to navigation:
```html
<a href="https://jsschrstrcks1.github.io/Allrecipes/cheese-builder.html"
   target="_blank" rel="noopener">
  Cheese Builder
</a>
```

---

## Resources

- [Allrecipes Cheese Builder](https://jsschrstrcks1.github.io/Allrecipes/cheese-builder.html)
- [Milk Substitution Integration Guide](./AGGREGATOR-INTEGRATION-PROMPT.md)
- [Cheese Recipe Guidelines](./CHEESE-RECIPE-GUIDELINES.md)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-22 | Initial adulterants.json with 156 additives |
| — | 2026-01-23 | Documentation created for Grandmasrecipes |

---

*"She looketh well to the ways of her household, and eateth not the bread of idleness." — Proverbs 31:27*
