# Cheese Recipe Guidelines - Summary

The Milk Substitution Tool automatically detects cheesemaking recipes to enable milk type switching (cow, goat, sheep) with ingredient adjustments.

## Related Tools

- **[Milk Substitution Tool](./AGGREGATOR-INTEGRATION-PROMPT.md)** - Switch between milk types with automatic ingredient adjustments
- **[Adulterant Companion](./ADULTERANT-COMPANION-GUIDE.md)** - Add herbs, spices, and flavorings to cheese recipes (156 additives across 9 categories)
- **[Cheese Builder](https://jsschrstrcks1.github.io/Allrecipes/cheese-builder.html)** - Interactive cheese recipe creation wizard

## Detection Methods (At Least One Required)

**1. Explicit Marker (Recommended)**
Add a `milk_substitutions` field with `enabled: true` and specify original and supported milk types.

**2. Category**
Set `category` to `"cheese"`.

**3. Tags**
Include cheesemaking-related tags such as "cheese," "cheesemaking," "artisan-cheese," "dairy," "curds," or "whey."

**4. Title Keywords**
Titles containing generic cheese terms (cheddar, mozzarella, feta, brie) or regional varieties are detected. Excluded patterns include "grilled cheese," "mac and cheese," and "cheesecake."

**5. Ingredient Detection**
Recipes combining milk with rennet or starter culture are automatically identified as cheesemaking recipes.

## Milk Type Recognition

The tool detects exotic milk varieties from ingredient names, including sheep's milk, goat milk, buffalo milk, camel milk, yak milk, and others. Generic "milk" defaults to cow milk.

## Verification

Test detection using `node scripts/test-milk-substitution.js` and verify the Milk Substitution Calculator panel appears on the recipe page.
