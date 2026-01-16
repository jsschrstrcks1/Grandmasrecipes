#!/usr/bin/env python3
"""
Build collection-based recipe shards from the master file.

This script splits recipes_master.json into separate shard files by collection,
enabling on-demand loading of only the recipes needed.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def build_recipe_shards(data_dir: Path):
    """Build collection-based recipe shard files."""

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
        shard_file = data_dir / f'recipes-{collection}.json'

        # Build shard with metadata
        shard = {
            'meta': {
                'collection': collection,
                'total_recipes': len(recipes),
                'generated': datetime.utcnow().isoformat() + 'Z',
                'source': 'recipes_master.json'
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
            'size_kb': round(size_kb)
        }

    # Update the index file with shard information
    index_file = data_dir / 'recipes_index.json'
    if index_file.exists():
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

    return shard_info


def build_ingredient_index_shards(data_dir: Path):
    """Optionally shard the ingredient index by collection."""

    index_file = data_dir / 'ingredient-index.json'
    if not index_file.exists():
        print("No ingredient-index.json found, skipping")
        return

    with open(index_file) as f:
        index = json.load(f)

    # Check if already small enough
    size_mb = os.path.getsize(index_file) / (1024 * 1024)
    if size_mb < 1.0:
        print(f"ingredient-index.json is only {size_mb:.1f}MB, no sharding needed")
        return

    print(f"\nIngredient index is {size_mb:.1f}MB - consider sharding if performance issues persist")


def main():
    data_dir = Path('data')

    print("=" * 60)
    print("Building Recipe Shards")
    print("=" * 60)

    shard_info = build_recipe_shards(data_dir)

    print("\n" + "=" * 60)
    print("Checking Ingredient Index")
    print("=" * 60)

    build_ingredient_index_shards(data_dir)

    print("\n" + "=" * 60)
    print("Shard Build Complete")
    print("=" * 60)
    print(f"\nGenerated {len(shard_info)} recipe shard files")
    print("\nNext steps:")
    print("1. Update script.js to load shards on-demand")
    print("2. Test recipe detail page loading")
    print("3. Commit and deploy")


if __name__ == '__main__':
    main()
