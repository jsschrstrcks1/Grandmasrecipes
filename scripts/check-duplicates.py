#!/usr/bin/env python3
"""
Cross-Repository Duplicate Checker

Checks for duplicate recipes across all collections:
- grandma-baker (local)
- mommom-baker
- granny-hudson
- all (Allrecipes)

Exact duplicates (same title) are flagged.
Variants (similar recipes with different names/sources) are OK.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

def normalize_title(title):
    """Normalize a title for comparison."""
    title = title.lower()
    # Remove common suffixes like collection markers
    title = re.sub(r'\s*\(.*?\)\s*$', '', title)  # Remove parenthetical suffixes
    title = re.sub(r'\s*-\s*(grandma|mommom|granny|all)$', '', title, flags=re.I)
    # Remove punctuation and extra whitespace
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def main():
    # Load recipes
    recipes_file = Path(__file__).parent.parent / 'data' / 'recipes_master.json'
    with open(recipes_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    recipes = data.get('recipes', [])
    print(f"Total recipes loaded: {len(recipes)}")
    print()

    # Group by collection
    by_collection = defaultdict(list)
    for r in recipes:
        collection = r.get('collection', 'unknown')
        by_collection[collection].append(r)

    print("Recipes by collection:")
    for coll, recs in sorted(by_collection.items()):
        print(f"  {coll}: {len(recs)}")
    print()

    # Find exact title duplicates (same normalized title, different collections)
    title_map = defaultdict(list)  # normalized_title -> [(id, collection, original_title)]

    for r in recipes:
        title = r.get('title', '')
        normalized = normalize_title(title)
        title_map[normalized].append({
            'id': r.get('id', ''),
            'collection': r.get('collection', ''),
            'title': title,
            'category': r.get('category', '')
        })

    # Find cross-collection duplicates (same title in different collections)
    cross_collection_dupes = []
    within_collection_dupes = []

    for norm_title, entries in title_map.items():
        if len(entries) > 1:
            collections = set(e['collection'] for e in entries)
            if len(collections) > 1:
                cross_collection_dupes.append((norm_title, entries))
            else:
                # Same title within same collection (could be variants or real dupes)
                within_collection_dupes.append((norm_title, entries))

    # Report cross-collection duplicates
    print("=" * 70)
    print("CROSS-COLLECTION DUPLICATES (same title in different collections)")
    print("These may be exact duplicates that should be consolidated.")
    print("=" * 70)
    print()

    if not cross_collection_dupes:
        print("No cross-collection duplicates found!")
    else:
        # Sort by number of occurrences (most duped first)
        cross_collection_dupes.sort(key=lambda x: -len(x[1]))

        for norm_title, entries in cross_collection_dupes[:50]:  # Top 50
            print(f"'{entries[0]['title']}' (normalized: '{norm_title}')")
            for e in entries:
                print(f"  - {e['collection']}: {e['id']} [{e['category']}]")
            print()

    print(f"\nTotal cross-collection duplicates: {len(cross_collection_dupes)}")
    print()

    # Report within-collection duplicates
    print("=" * 70)
    print("WITHIN-COLLECTION DUPLICATES (same title within one collection)")
    print("These are likely true duplicates or variant entries to review.")
    print("=" * 70)
    print()

    if not within_collection_dupes:
        print("No within-collection duplicates found!")
    else:
        within_collection_dupes.sort(key=lambda x: -len(x[1]))

        for norm_title, entries in within_collection_dupes[:30]:  # Top 30
            print(f"'{entries[0]['title']}' in {entries[0]['collection']}")
            for e in entries:
                print(f"  - ID: {e['id']} [{e['category']}]")
            print()

    print(f"\nTotal within-collection duplicates: {len(within_collection_dupes)}")

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total recipes: {len(recipes)}")
    print(f"Unique normalized titles: {len(title_map)}")
    print(f"Cross-collection duplicates: {len(cross_collection_dupes)}")
    print(f"Within-collection duplicates: {len(within_collection_dupes)}")
    print()

    # Check specific known family recipe names across collections
    family_recipes = [
        'oatmeal cookies', 'chocolate chip cookies', 'banana bread',
        'meatloaf', 'mac and cheese', 'chicken soup', 'apple pie',
        'cornbread', 'biscuits', 'gravy', 'fried chicken', 'pot roast'
    ]

    print("=" * 70)
    print("FAMILY RECIPE CHECK (common recipes across collections)")
    print("=" * 70)
    print()

    for family_name in family_recipes:
        matches = []
        for norm_title, entries in title_map.items():
            if family_name in norm_title:
                matches.extend(entries)

        if matches:
            collections = set(m['collection'] for m in matches)
            if len(collections) > 1:
                print(f"'{family_name}' found in {len(collections)} collections:")
                for m in matches[:10]:  # Limit to 10
                    print(f"  - {m['collection']}: {m['title']}")
                print()

if __name__ == '__main__':
    main()
