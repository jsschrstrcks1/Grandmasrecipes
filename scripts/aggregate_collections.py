#!/usr/bin/env python3
"""
Aggregate Family Recipe Collections

Fetches recipes from all family recipe repositories and merges them into
the hub's recipes_master.json for unified search and display.

Supports both monolithic (recipes.json) and sharded (recipes-index.json +
recipes-{category}.json) repository formats.

Usage:
    python scripts/aggregate_collections.py           # Full aggregation
    python scripts/aggregate_collections.py --dry-run # Preview without saving
    python scripts/aggregate_collections.py --local-only # Skip remote fetch

Remote Sources:
    - MomsRecipes: https://jsschrstrcks1.github.io/MomsRecipes/data/recipes.json
    - Grannysrecipes: https://jsschrstrcks1.github.io/Grannysrecipes/data/recipes.json
    - Allrecipes: https://jsschrstrcks1.github.io/Allrecipes/data/ (sharded)

Sharded Repository Support:
    Repositories can use category-based sharding for better performance:
    - data/recipes-index.json: Minimal metadata + shard manifest
    - data/recipes-{category}.json: Full recipes per category

    This script auto-detects sharded repos and fetches all category shards.

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
from concurrent.futures import ThreadPoolExecutor, as_completed

# Collection configuration
# Each collection can be:
#   - 'url': Direct path to recipes.json (monolithic)
#   - 'sharded': True to auto-detect and fetch sharded format
#   - 'index_url': Override URL for recipes-index.json (if sharded)
REMOTE_COLLECTIONS = {
    'mommom-baker': {
        'url': 'https://jsschrstrcks1.github.io/MomsRecipes/data/recipes.json',
        'display_name': 'MomMom Baker',
        'base_url': 'https://jsschrstrcks1.github.io/MomsRecipes/',
        'legacy_ids': ['mommom', 'mommom-baker'],
        'sharded': False  # Can be upgraded to sharded later
    },
    'granny-hudson': {
        'url': 'https://jsschrstrcks1.github.io/Grannysrecipes/granny/recipes_master.json',
        'display_name': 'Granny Hudson',
        'base_url': 'https://jsschrstrcks1.github.io/Grannysrecipes/',
        'legacy_ids': ['granny', 'granny-hudson'],
        'sharded': False  # Can be upgraded to sharded later
    },
    'all': {
        'url': 'https://jsschrstrcks1.github.io/Allrecipes/data/recipes.json',
        'index_url': 'https://jsschrstrcks1.github.io/Allrecipes/data/recipes-index.json',
        'display_name': 'Other Recipes',
        'base_url': 'https://jsschrstrcks1.github.io/Allrecipes/',
        'legacy_ids': ['reference', 'all', 'other'],
        'sharded': True  # Allrecipes uses sharded format
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


def fetch_json(url: str, timeout: int = 30) -> Tuple[Optional[Dict], Optional[str]]:
    """Fetch JSON data from a URL.

    Returns:
        Tuple of (data dict, error message or None)
    """
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'GrandmasRecipes-Aggregator/1.0'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data, None

    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return None, f"URL error: {e.reason}"
    except json.JSONDecodeError as e:
        return None, f"JSON decode error: {e}"
    except Exception as e:
        return None, f"Error: {e}"


def check_sharded_repo(base_url: str, timeout: int = 30) -> Tuple[bool, Optional[Dict]]:
    """Check if a repository uses sharded format.

    Looks for recipes-index.json which indicates sharded structure.

    Returns:
        Tuple of (is_sharded, index_data or None)
    """
    index_url = base_url.rstrip('/') + '/data/recipes-index.json'
    data, error = fetch_json(index_url, timeout)

    if error:
        return False, None

    # Check if it has the sharded structure (shards array)
    if isinstance(data, dict) and 'shards' in data:
        return True, data

    return False, None


def fetch_sharded_recipes(base_url: str, index_data: Dict, verbose: bool = False,
                          timeout: int = 30) -> Tuple[List[Dict], Optional[str]]:
    """Fetch all recipes from a sharded repository.

    Reads the shard manifest from index_data and fetches all category shards
    in parallel for efficiency.

    Args:
        base_url: Base URL of the repository (e.g., 'https://...github.io/Allrecipes/')
        index_data: The parsed recipes-index.json data
        verbose: Print detailed progress
        timeout: Request timeout in seconds

    Returns:
        Tuple of (all recipes list, error message or None)
    """
    shards = index_data.get('shards', [])
    if not shards:
        return [], "No shards defined in index"

    data_url = base_url.rstrip('/') + '/data/'
    all_recipes = []
    errors = []

    def fetch_shard(shard: Dict) -> Tuple[str, List[Dict], Optional[str]]:
        """Fetch a single shard."""
        shard_file = shard.get('file', f"recipes-{shard.get('category', 'unknown')}.json")
        shard_url = data_url + shard_file

        if verbose:
            print(f"      Fetching shard: {shard_file}")

        data, error = fetch_json(shard_url, timeout)
        if error:
            return shard_file, [], error

        # Extract recipes from shard
        if isinstance(data, dict):
            recipes = data.get('recipes', [])
        elif isinstance(data, list):
            recipes = data
        else:
            return shard_file, [], f"Unexpected shard format: {type(data)}"

        return shard_file, recipes, None

    # Fetch shards in parallel for efficiency
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_shard, shard): shard for shard in shards}

        for future in as_completed(futures):
            shard = futures[future]
            try:
                shard_file, recipes, error = future.result()
                if error:
                    errors.append(f"{shard_file}: {error}")
                    if verbose:
                        print(f"        ERROR: {shard_file}: {error}")
                else:
                    all_recipes.extend(recipes)
                    if verbose:
                        print(f"        OK: {shard_file} ({len(recipes)} recipes)")
            except Exception as e:
                errors.append(f"{shard.get('file', 'unknown')}: {e}")

    if errors and not all_recipes:
        return [], f"Failed to fetch any shards: {'; '.join(errors)}"

    return all_recipes, None


def fetch_collection_recipes(collection_id: str, config: Dict,
                             verbose: bool = False) -> Tuple[List[Dict], Dict]:
    """Fetch recipes from a collection, auto-detecting sharded vs monolithic.

    Args:
        collection_id: The collection identifier
        config: Collection configuration dict
        verbose: Print detailed progress

    Returns:
        Tuple of (recipes list, metadata dict with fetch info)
    """
    base_url = config.get('base_url', '')
    is_sharded = config.get('sharded', False)
    metadata = {
        'format': 'unknown',
        'shard_count': 0,
        'error': None
    }

    # Try sharded format first if configured or if we should auto-detect
    if is_sharded:
        # Use explicit index URL if provided, otherwise construct from base_url
        index_url = config.get('index_url')
        if index_url:
            index_data, error = fetch_json(index_url)
            if not error and index_data and 'shards' in index_data:
                if verbose:
                    print(f"    Sharded format detected ({len(index_data.get('shards', []))} shards)")
                metadata['format'] = 'sharded'
                metadata['shard_count'] = len(index_data.get('shards', []))

                recipes, error = fetch_sharded_recipes(base_url, index_data, verbose)
                if error:
                    metadata['error'] = error
                    # Fall back to monolithic
                    if verbose:
                        print(f"    Shard fetch failed, trying monolithic fallback...")
                else:
                    return recipes, metadata
        else:
            # Auto-detect sharded format
            is_sharded_detected, index_data = check_sharded_repo(base_url)
            if is_sharded_detected and index_data:
                if verbose:
                    print(f"    Sharded format auto-detected ({len(index_data.get('shards', []))} shards)")
                metadata['format'] = 'sharded'
                metadata['shard_count'] = len(index_data.get('shards', []))

                recipes, error = fetch_sharded_recipes(base_url, index_data, verbose)
                if error:
                    metadata['error'] = error
                else:
                    return recipes, metadata

    # Monolithic format (or fallback)
    url = config.get('url')
    if not url:
        metadata['error'] = "No URL configured"
        return [], metadata

    if verbose:
        print(f"    Fetching monolithic: {url}")

    metadata['format'] = 'monolithic'
    recipes, error = fetch_remote_recipes(url)
    if error:
        metadata['error'] = error
        return [], metadata

    return recipes, metadata


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
    fetch_metadata = {}

    if not args.local_only:
        print()
        print("Fetching remote collections...")

        for collection_id, config in REMOTE_COLLECTIONS.items():
            print(f"  {config['display_name']} ({collection_id})...")

            # Use new sharded-aware fetch function
            recipes, metadata = fetch_collection_recipes(
                collection_id, config, verbose=args.verbose
            )
            fetch_metadata[collection_id] = metadata

            if metadata.get('error'):
                print(f"    ERROR: {metadata['error']}")
                print(f"    Skipping this collection.")
                continue

            # Show format info
            if metadata.get('format') == 'sharded':
                print(f"    Format: sharded ({metadata.get('shard_count', 0)} category shards)")
            else:
                print(f"    Format: monolithic")

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

    # Add fetch metadata for each collection
    meta['collection_formats'] = {
        cid: {
            'format': fm.get('format', 'unknown'),
            'shard_count': fm.get('shard_count', 0)
        }
        for cid, fm in fetch_metadata.items()
        if not fm.get('error')
    }

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
