#!/usr/bin/env python3
"""
Build collection-based recipe shards from the master file.

This script implements two-level sharding:
- Small collections (< 1000 recipes): Single collection shard
- Large collections (>= 1000 recipes): Category-based sub-shards

This enables on-demand loading of only the recipes needed.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Collections that should be sub-sharded by category
LARGE_COLLECTION_THRESHOLD = 1000  # recipes


def build_recipe_shards(data_dir: Path):
    """Build collection-based recipe shard files with optional category sub-shards."""

    master_file = data_dir / 'recipes_master.json'

    with open(master_file) as f:
        master = json.load(f)

    # Group recipes by collection
    by_collection = defaultdict(list)
    for recipe in master['recipes']:
        collection = recipe.get('collection', 'unknown')
        by_collection[collection].append(recipe)

    print(f"Building shards from {len(master['recipes'])} recipes:")

    shard_info = {}

    for collection, recipes in sorted(by_collection.items()):
        if len(recipes) >= LARGE_COLLECTION_THRESHOLD:
            # Large collection - create category sub-shards
            sub_shard_info = build_category_subshards(data_dir, collection, recipes)
            shard_info[collection] = sub_shard_info
        else:
            # Small collection - single shard file
            shard_file = data_dir / f'recipes-{collection}.json'

            shard = {
                'meta': {
                    'collection': collection,
                    'total_recipes': len(recipes),
                    'generated': datetime.utcnow().isoformat() + 'Z',
                    'source': 'recipes_master.json',
                    'sharded_by_category': False
                },
                'recipes': recipes
            }

            with open(shard_file, 'w') as f:
                json.dump(shard, f, indent=2)

            size_kb = os.path.getsize(shard_file) / 1024
            print(f"  {collection}: {len(recipes)} recipes ({size_kb:.0f} KB)")

            shard_info[collection] = {
                'file': f'recipes-{collection}.json',
                'count': len(recipes),
                'size_kb': round(size_kb),
                'sharded_by_category': False
            }

    # Update the index file with shard information
    update_index_with_shard_info(data_dir, shard_info)

    return shard_info


def build_category_subshards(data_dir: Path, collection: str, recipes: list) -> dict:
    """Build category-based sub-shards for a large collection."""

    print(f"\n  {collection}: {len(recipes)} recipes (sub-sharding by category)")

    # Group by category
    by_category = defaultdict(list)
    for recipe in recipes:
        category = recipe.get('category', 'unknown')
        by_category[category].append(recipe)

    category_shards = {}
    total_size_kb = 0

    for category, cat_recipes in sorted(by_category.items()):
        shard_file = data_dir / f'recipes-{collection}-{category}.json'

        shard = {
            'meta': {
                'collection': collection,
                'category': category,
                'total_recipes': len(cat_recipes),
                'generated': datetime.utcnow().isoformat() + 'Z',
                'source': 'recipes_master.json'
            },
            'recipes': cat_recipes
        }

        with open(shard_file, 'w') as f:
            json.dump(shard, f, indent=2)

        size_kb = os.path.getsize(shard_file) / 1024
        total_size_kb += size_kb
        print(f"    {category}: {len(cat_recipes)} recipes ({size_kb:.0f} KB)")

        category_shards[category] = {
            'file': f'recipes-{collection}-{category}.json',
            'count': len(cat_recipes),
            'size_kb': round(size_kb)
        }

    return {
        'sharded_by_category': True,
        'total_count': len(recipes),
        'total_size_kb': round(total_size_kb),
        'categories': category_shards
    }


def update_index_with_shard_info(data_dir: Path, shard_info: dict):
    """Update the recipes index file with shard metadata."""

    index_file = data_dir / 'recipes_index.json'
    if not index_file.exists():
        return

    with open(index_file) as f:
        index = json.load(f)

    # Add shard metadata
    if 'meta' not in index:
        index['meta'] = {}

    index['meta']['shards'] = shard_info
    index['meta']['sharding_enabled'] = True
    index['meta']['last_shard_build'] = datetime.utcnow().isoformat() + 'Z'

    with open(index_file, 'w') as f:
        json.dump(index, f, indent=2)

    print(f"\nUpdated {index_file.name} with shard metadata")


def cleanup_old_shards(data_dir: Path):
    """Remove old single-collection shard files for collections now using sub-shards."""

    # Collections that are now sub-sharded
    large_collections = ['mommom-baker', 'all']

    for coll in large_collections:
        old_shard = data_dir / f'recipes-{coll}.json'
        if old_shard.exists():
            os.remove(old_shard)
            print(f"Removed old shard: {old_shard.name}")


def main():
    data_dir = Path('data')

    print("=" * 60)
    print("Building Recipe Shards (Two-Level)")
    print("=" * 60)
    print(f"Threshold for category sub-sharding: {LARGE_COLLECTION_THRESHOLD} recipes")
    print()

    shard_info = build_recipe_shards(data_dir)

    print("\n" + "=" * 60)
    print("Cleaning Up Old Shards")
    print("=" * 60)

    cleanup_old_shards(data_dir)

    print("\n" + "=" * 60)
    print("Shard Build Complete")
    print("=" * 60)

    # Summary
    small_collections = [k for k, v in shard_info.items() if not v.get('sharded_by_category')]
    large_collections = [k for k, v in shard_info.items() if v.get('sharded_by_category')]

    print(f"\nSmall collections (single shard): {', '.join(small_collections)}")
    print(f"Large collections (category sub-shards): {', '.join(large_collections)}")

    total_files = len(small_collections)
    for coll in large_collections:
        total_files += len(shard_info[coll].get('categories', {}))

    print(f"\nTotal shard files generated: {total_files}")


if __name__ == '__main__':
    main()
