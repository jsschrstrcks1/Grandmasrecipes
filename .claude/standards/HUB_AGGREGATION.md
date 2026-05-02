# Hub Aggregation — Grandma's Kitchen

Grandma's repo can serve as the **central site** that aggregates recipes from
the other family collections.

## FAMILY_COLLECTIONS Array

```javascript
const FAMILY_COLLECTIONS = [
  { id: 'grandma-baker', name: "Grandma Baker", local: true },
  { id: 'mommom-baker',  name: "MomMom Baker",
    url: 'https://jsschrstrcks1.github.io/MomsRecipes/data/recipes.json' },
  { id: 'granny-hudson', name: "Granny Hudson",
    url: 'https://jsschrstrcks1.github.io/Grannysrecipes/data/recipes.json' },
  { id: 'all',           name: "Other Recipes",
    url: 'https://jsschrstrcks1.github.io/Allrecipes/data/recipes.json' }
];
```

## Image Path Resolution

When aggregating, **image paths must be resolved to absolute URLs** for remote
collections. The `getCollectionImagePath()` helper in `script.js` returns:

- `'data/'` for the local collection (`local: true`).
- The remote collection's GitHub Pages base URL for everything else.

## Cross-repo standards

See [`.claude/CROSS_REPO_STANDARDS.md`](../CROSS_REPO_STANDARDS.md) for the
shared schema rules every collection follows. The aggregator assumes:

- Every recipe carries `collection`, `collection_display`, `id`, `title`,
  `category`, `ingredients`, `instructions`.
- Categories use the shared vocabulary: `appetizers, beverages, breads,
  breakfast, desserts, mains, salads, sides, soups, snacks`.
- Image references are relative to the **owning** repo's `data/` folder.
