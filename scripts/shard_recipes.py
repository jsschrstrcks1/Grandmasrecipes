#!/usr/bin/env python3
"""
Shard recipes by category for faster initial page load.

Creates:
- recipes-index.json: Lightweight index with minimal fields for grid display (~300-500 KB)
- recipes-{category}.json: Full recipe data per category (loaded on-demand)

This reduces initial page load from ~7 MB to ~400 KB, with category data
loaded lazily when needed.
"""

import json
import os
from pathlib import Path
from collections import defaultdict

# Fields for lightweight index (minimal for grid display)
# Keep this as small as possible - full data loaded from shards
INDEX_FIELDS = [
    'id',
    'collection',
    'title',
    'category',
    'description',     # For grid card display
    'total_time',      # For time display/filtering
    'variant_of',      # For variant grouping
]

# Additional fields to include but truncate/simplify
TRUNCATE_FIELDS = {
    'image_refs': 1,   # Only first image for grid thumbnail
}

# Normalize category names (some remote repos use non-standard names)
CATEGORY_MAP = {
    'main-dishes': 'mains',
    'vegetables': 'sides',
    'cookies': 'desserts',
    'cakes': 'desserts',
    'candy': 'desserts',
    'frostings': 'desserts',
    'fish': 'mains',
    'shellfish': 'mains',
    'meat': 'mains',
    'eggs': 'breakfast',
    'pasta': 'mains',
    'sandwiches': 'mains',
    'legumes': 'sides',
    'sauces': 'condiments',
    'preserves': 'condiments',
    'canning': 'condiments',
    'basics': 'reference',
    'remedies': 'reference',
}

VALID_CATEGORIES = [
    'appetizers', 'beverages', 'breads', 'breakfast', 'desserts',
    'mains', 'salads', 'sides', 'soups', 'snacks', 'condiments',
    'tips', 'reference'
]


def normalize_category(category):
    """Normalize category to standard set."""
    if not category:
        return 'reference'
    cat = category.lower().strip()
    return CATEGORY_MAP.get(cat, cat if cat in VALID_CATEGORIES else 'reference')


def create_index_entry(recipe):
    """Create lightweight index entry from full recipe."""
    entry = {}
    for field in INDEX_FIELDS:
        if field in recipe:
            entry[field] = recipe[field]

    # Add truncated fields
    for field, max_items in TRUNCATE_FIELDS.items():
        if field in recipe and recipe[field]:
            value = recipe[field]
            if isinstance(value, list):
                entry[field] = value[:max_items]
            else:
                entry[field] = value

    return entry


def shard_recipes(master_path, output_dir):
    """Shard recipes by category."""
    print(f"Reading {master_path}...")
    with open(master_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    meta = data.get('meta', {})
    recipes = data.get('recipes', [])
    print(f"Processing {len(recipes)} recipes...")

    # Group recipes by normalized category
    by_category = defaultdict(list)
    index_entries = []

    for recipe in recipes:
        original_cat = recipe.get('category', '')
        normalized_cat = normalize_category(original_cat)

        # Store normalized category in recipe
        recipe['category'] = normalized_cat

        # Add to category shard
        by_category[normalized_cat].append(recipe)

        # Create index entry
        index_entry = create_index_entry(recipe)
        index_entry['category'] = normalized_cat
        index_entries.append(index_entry)

    # Create shard manifest
    shards = []
    for category in sorted(by_category.keys()):
        count = len(by_category[category])
        shards.append({
            'category': category,
            'file': f'recipes-{category}.json',
            'count': count
        })

    # Write lightweight index
    index_data = {
        'meta': {
            **meta,
            'sharded': True,
            'shard_count': len(shards),
            'index_fields': INDEX_FIELDS,
        },
        'shards': shards,
        'recipes': index_entries
    }

    index_path = output_dir / 'recipes-index.json'
    print(f"\nWriting {index_path}...")
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, separators=(',', ':'))
    index_size = os.path.getsize(index_path)
    print(f"  Size: {index_size:,} bytes ({index_size/1024:.1f} KB)")

    # Write category shards
    print(f"\nWriting {len(shards)} category shards...")
    total_shard_size = 0
    for shard in shards:
        category = shard['category']
        shard_recipes = by_category[category]

        shard_data = {
            'category': category,
            'count': len(shard_recipes),
            'recipes': shard_recipes
        }

        shard_path = output_dir / shard['file']
        with open(shard_path, 'w', encoding='utf-8') as f:
            json.dump(shard_data, f, separators=(',', ':'))

        shard_size = os.path.getsize(shard_path)
        total_shard_size += shard_size
        print(f"  {shard['file']}: {shard['count']} recipes, {shard_size/1024:.1f} KB")

    # Also keep the old recipes_index.json format for backwards compatibility
    # but now it just references the sharded format
    compat_index = {
        'meta': {
            **meta,
            'sharded': True,
            'note': 'Use recipes-index.json for sharded loading'
        },
        'recipes': index_entries
    }
    compat_path = output_dir / 'recipes_index.json'
    print(f"\nWriting backwards-compatible {compat_path}...")
    with open(compat_path, 'w', encoding='utf-8') as f:
        json.dump(compat_index, f, separators=(',', ':'))
    compat_size = os.path.getsize(compat_path)

    # Summary
    master_size = os.path.getsize(master_path)
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Original master:     {master_size/1024/1024:.1f} MB")
    print(f"Lightweight index:   {index_size/1024:.1f} KB  (initial load)")
    print(f"Total shards:        {total_shard_size/1024/1024:.1f} MB across {len(shards)} files")
    print(f"Backwards-compat:    {compat_size/1024:.1f} KB")
    print(f"\nInitial load reduced from {master_size/1024/1024:.1f} MB to {index_size/1024:.1f} KB")
    print(f"Reduction: {(1 - index_size/master_size)*100:.1f}%")

    return index_path, shards


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    data_dir = project_dir / 'data'

    master_path = data_dir / 'recipes_master.json'

    if not master_path.exists():
        print(f"ERROR: {master_path} not found")
        return 1

    shard_recipes(master_path, data_dir)

    print("\nNext steps:")
    print("  1. Update script.js to use sharded loading")
    print("  2. Test the site locally")
    print("  3. Commit and deploy")

    return 0


if __name__ == '__main__':
    exit(main())
