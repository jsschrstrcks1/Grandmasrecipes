# Recipe Schema — Grandma's Kitchen

```json
{
  "id": "recipe-slug",
  "collection": "grandma-baker",
  "collection_display": "Grandma Baker",
  "title": "Recipe Name",
  "category": "desserts",
  "image_refs": ["Grandmas-recipes - 12.jpeg"],
  "ingredients": [],
  "instructions": [],
  "notes": []
}
```

## Categories

```
appetizers, beverages, breads, breakfast, desserts,
mains, salads, sides, soups, snacks
```

## Collection ID format

```
WRONG:   collection: "grandma"        (legacy, do not use)
RIGHT:   collection: "grandma-baker"  (current)
```

## Validation

```bash
python scripts/validate-recipes.py
```
