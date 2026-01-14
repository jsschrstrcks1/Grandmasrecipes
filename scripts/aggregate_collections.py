#!/usr/bin/env python3
"""
Aggregate Family Recipe Collections

Fetches recipes from all family recipe repositories and merges them into
the hub's recipes_master.json for unified search and display.

Usage:
    python scripts/aggregate_collections.py           # Full aggregation
    python scripts/aggregate_collections.py --dry-run # Preview without saving
    python scripts/aggregate_collections.py --local-only # Skip remote fetch

Remote Sources:
    - MomsRecipes: https://jsschrstrcks1.github.io/MomsRecipes/data/recipes.json
    - Grannysrecipes: https://jsschrstrcks1.github.io/Grannysrecipes/data/recipes.json
    - Allrecipes: https://jsschrstrcks1.github.io/Allrecipes/data/recipes.json

Output:
    - Updates data/recipes_master.json with merged recipes
    - Updates meta.total_recipes count
    - Normalizes collection IDs to standard format

After running, rebuild indexes:
    python scripts/generate_index.py
    python scripts/build-ingredient-index.py
    python scripts/build-pagefind.py
"""

import json
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# Collection configuration
REMOTE_COLLECTIONS = {
    'mommom-baker': {
        'url': 'https://jsschrstrcks1.github.io/MomsRecipes/data/recipes.json',
        'display_name': 'MomMom Baker',
        'base_url': 'https://jsschrstrcks1.github.io/MomsRecipes/',
        'legacy_ids': ['mommom', 'mommom-baker']
    },
    'granny-hudson': {
        'url': 'https://jsschrstrcks1.github.io/Grannysrecipes/granny/recipes_master.json',
        'display_name': 'Granny Hudson',
        'base_url': 'https://jsschrstrcks1.github.io/Grannysrecipes/',
        'legacy_ids': ['granny', 'granny-hudson']
    },
    'all': {
        'url': 'https://jsschrstrcks1.github.io/Allrecipes/data/recipes.json',
        'display_name': 'Other Recipes',
        'base_url': 'https://jsschrstrcks1.github.io/Allrecipes/',
        'legacy_ids': ['reference', 'all', 'other']
    }
}

LOCAL_COLLECTION = {
    'id': 'grandma-baker',
    'display_name': 'Grandma Baker',
    'legacy_ids': ['grandma', 'grandma-baker']
}

# Collection ID normalization map
COLLECTION_ID_MAP = {
    'grandma': 'grandma-baker',
    'mommom': 'mommom-baker',
    'granny': 'granny-hudson',
    'reference': 'all',
    'other': 'all',
}


def normalize_collection_id(collection_id: str) -> str:
    """Normalize legacy collection IDs to standard format."""
    return COLLECTION_ID_MAP.get(collection_id, collection_id)


def fetch_remote_recipes(url: str, timeout: int = 30) -> Tuple[List[Dict], Optional[str]]:
    """Fetch recipes from a remote URL.

    Returns:
        Tuple of (recipes list, error message or None)
    """
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'GrandmasRecipes-Aggregator/1.0'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode('utf-8'))

            # Handle both formats: {recipes: [...]} and [...]
            if isinstance(data, dict):
                recipes = data.get('recipes', [])
            elif isinstance(data, list):
                recipes = data
            else:
                return [], f"Unexpected data format: {type(data)}"

            return recipes, None

    except urllib.error.URLError as e:
        return [], f"URL error: {e.reason}"
    except urllib.error.HTTPError as e:
        return [], f"HTTP {e.code}: {e.reason}"
    except json.JSONDecodeError as e:
        return [], f"JSON decode error: {e}"
    except Exception as e:
        return [], f"Error: {e}"


def resolve_image_paths(recipe: Dict, base_url: str) -> Dict:
    """Convert relative image paths to absolute URLs for remote collections."""
    if 'image_refs' in recipe and recipe['image_refs']:
        resolved_refs = []
        for ref in recipe['image_refs']:
            # Skip if already absolute URL
            if ref.startswith('http://') or ref.startswith('https://'):
                resolved_refs.append(ref)
            else:
                # Convert relative path to absolute URL
                resolved_refs.append(f"{base_url}data/{ref}")
        recipe['image_refs'] = resolved_refs
    return recipe


def normalize_recipe(recipe: Dict, collection_id: str, display_name: str, base_url: Optional[str] = None) -> Dict:
    """Normalize a recipe's collection fields and image paths."""
    # Normalize collection ID
    recipe['collection'] = collection_id
    recipe['collection_display'] = display_name

    # Resolve image paths for remote collections
    if base_url:
        recipe = resolve_image_paths(recipe, base_url)

    return recipe


def load_local_recipes(master_path: Path) -> Tuple[Dict, List[Dict]]:
    """Load local recipes from recipes_master.json.

    Returns:
        Tuple of (meta dict, recipes list)
    """
    if not master_path.exists():
        return {}, []

    with open(master_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    meta = data.get('meta', {})
    recipes = data.get('recipes', [])

    return meta, recipes


def filter_local_recipes(recipes: List[Dict]) -> List[Dict]:
    """Keep only local (grandma-baker) recipes from the master file.

    Remote recipes will be re-fetched fresh.
    """
    local_ids = LOCAL_COLLECTION['legacy_ids']
    return [r for r in recipes if normalize_collection_id(r.get('collection', '')) == 'grandma-baker']


def recipe_signature(recipe: Dict) -> str:
    """Create a signature for exact duplicate detection.

    Only drops recipes that are truly identical (same id, collection, title,
    and ingredients). Variants with same ID but different content are kept.
    """
    # Use key fields that define a unique recipe
    recipe_id = recipe.get('id', '')
    collection = recipe.get('collection', '')
    title = recipe.get('title', '')
    # Use first 3 ingredients as part of signature to detect variants
    ingredients = recipe.get('ingredients', [])[:3]
    ingredients_str = '|'.join(str(i) for i in ingredients)
    return f"{recipe_id}::{collection}::{title}::{ingredients_str}"


def merge_recipes(local_recipes: List[Dict], remote_recipes: Dict[str, List[Dict]]) -> List[Dict]:
    """Merge local and remote recipes, avoiding exact duplicates only.

    Variants of the same recipe (same ID but different content) are kept.
    Only truly identical recipes are dropped.
    """
    # Build set of signatures from local recipes
    seen_signatures = {recipe_signature(r) for r in local_recipes}

    merged = list(local_recipes)

    for collection_id, recipes in remote_recipes.items():
        for recipe in recipes:
            sig = recipe_signature(recipe)
            if sig not in seen_signatures:
                merged.append(recipe)
                seen_signatures.add(sig)

    return merged


def count_by_collection(recipes: List[Dict]) -> Dict[str, int]:
    """Count recipes by collection."""
    counts = {}
    for r in recipes:
        col = r.get('collection', 'unknown')
        counts[col] = counts.get(col, 0) + 1
    return counts


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Aggregate family recipe collections into hub repository'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Preview changes without saving'
    )
    parser.add_argument(
        '--local-only', '-l',
        action='store_true',
        help='Skip fetching remote collections (normalize local only)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed progress'
    )

    args = parser.parse_args()

    # Paths
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    master_path = project_dir / 'data' / 'recipes_master.json'

    print("=" * 60)
    print("RECIPE COLLECTION AGGREGATOR")
    print("=" * 60)
    print()

    # Load local recipes
    print(f"Loading local recipes from {master_path}...")
    meta, all_local_recipes = load_local_recipes(master_path)

    # Filter to only keep grandma-baker recipes (remote will be re-fetched)
    local_recipes = filter_local_recipes(all_local_recipes)
    print(f"  Local (grandma-baker) recipes: {len(local_recipes)}")

    # Normalize local recipes
    for recipe in local_recipes:
        normalize_recipe(recipe, 'grandma-baker', LOCAL_COLLECTION['display_name'])

    # Fetch remote collections
    remote_recipes = {}

    if not args.local_only:
        print()
        print("Fetching remote collections...")

        for collection_id, config in REMOTE_COLLECTIONS.items():
            print(f"  {config['display_name']} ({collection_id})...")
            print(f"    URL: {config['url']}")

            recipes, error = fetch_remote_recipes(config['url'])

            if error:
                print(f"    ERROR: {error}")
                print(f"    Skipping this collection.")
                continue

            # Normalize each recipe
            normalized = []
            for recipe in recipes:
                normalized.append(normalize_recipe(
                    recipe,
                    collection_id,
                    config['display_name'],
                    config['base_url']
                ))

            remote_recipes[collection_id] = normalized
            print(f"    Fetched: {len(normalized)} recipes")

    # Merge all recipes
    print()
    print("Merging recipes...")
    merged = merge_recipes(local_recipes, remote_recipes)
    print(f"  Total merged: {len(merged)} recipes")

    # Count by collection
    counts = count_by_collection(merged)
    print()
    print("Recipes by collection:")
    for col, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {col}: {count}")

    # Update meta
    meta['total_recipes'] = len(merged)
    meta['last_updated'] = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    meta['last_aggregation'] = datetime.now(timezone.utc).isoformat()
    meta['collection_counts'] = counts

    # Prepare output
    output_data = {
        'meta': meta,
        'recipes': merged
    }

    if args.dry_run:
        print()
        print("DRY RUN - No changes saved")
        print(f"Would write {len(merged)} recipes to {master_path}")
    else:
        print()
        print(f"Saving to {master_path}...")
        with open(master_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print("  Done!")

        print()
        print("Next steps:")
        print("  1. python scripts/generate_index.py")
        print("  2. python scripts/build-ingredient-index.py")
        print("  3. python scripts/build-pagefind.py")
        print("  4. python scripts/validate-recipes.py")

    print()
    print("=" * 60)
    print(f"SUMMARY: {len(merged)} total recipes")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
