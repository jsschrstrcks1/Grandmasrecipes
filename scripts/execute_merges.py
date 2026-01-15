#!/usr/bin/env python3
"""
Execute Recipe Merges and Variant Links

Based on the analysis from analyze_duplicates.py, this script:
1. Merges duplicate recipes (keeping canonical, maintaining provenance)
2. Links variants with variant_of references
3. Creates an audit log of all changes

Usage:
    python scripts/execute_merges.py [--dry-run]
"""

import json
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict


def load_data():
    """Load recipes and analysis data."""
    with open('data/recipes_master.json') as f:
        recipes_data = json.load(f)

    with open('data/duplicate_analysis.json') as f:
        analysis = json.load(f)

    return recipes_data, analysis


def execute_merges(recipes_data, analysis, dry_run=False):
    """Execute merges and variant links."""
    recipes = recipes_data.get('recipes', [])
    recipes_by_id = {r['id']: r for r in recipes}

    merge_log = {
        'timestamp': datetime.now().isoformat(),
        'dry_run': dry_run,
        'merges': [],
        'variants_linked': [],
        'errors': []
    }

    ids_to_delete = set()
    recipe_groups = analysis.get('recipe_groups', [])

    for group in recipe_groups:
        canonical_id = group['canonical']['id']
        canonical = recipes_by_id.get(canonical_id)

        if not canonical:
            merge_log['errors'].append(f"Canonical recipe not found: {canonical_id}")
            continue

        # Process merges
        for merge_entry in group.get('merge_into_canonical', []):
            merge_id = merge_entry['id']
            merge_recipe = recipes_by_id.get(merge_id)

            if not merge_recipe:
                merge_log['errors'].append(f"Merge recipe not found: {merge_id}")
                continue

            # Initialize sources array if not present
            if 'sources' not in canonical:
                canonical['sources'] = [group['canonical']['source']]

            # Add source from merged recipe
            merge_source = merge_entry['source']
            if merge_source not in canonical['sources']:
                canonical['sources'].append(merge_source)

            # Combine image_refs
            if 'image_refs' not in canonical:
                canonical['image_refs'] = []
            merge_images = merge_recipe.get('image_refs', [])
            for img in merge_images:
                if img not in canonical['image_refs']:
                    canonical['image_refs'].append(img)

            # Add source_notes if not present
            if 'source_notes' not in canonical:
                canonical['source_notes'] = f"Consolidated from multiple sources: {', '.join(canonical['sources'])}"
            else:
                canonical['source_notes'] = f"Consolidated from multiple sources: {', '.join(canonical['sources'])}"

            # Mark for deletion
            ids_to_delete.add(merge_id)

            merge_log['merges'].append({
                'canonical_id': canonical_id,
                'merged_id': merge_id,
                'merged_source': merge_source,
                'reason': merge_entry.get('scores', {}).get('reason', 'Unknown')
            })

        # Process variants
        for variant_entry in group.get('keep_as_variants', []):
            variant_id = variant_entry['id']
            variant_recipe = recipes_by_id.get(variant_id)

            if not variant_recipe:
                merge_log['errors'].append(f"Variant recipe not found: {variant_id}")
                continue

            # Add variant_of reference
            variant_recipe['variant_of'] = canonical_id
            variant_recipe['variant_note'] = variant_entry.get('variant_reason', 'Similar recipe with variations')

            merge_log['variants_linked'].append({
                'variant_id': variant_id,
                'canonical_id': canonical_id,
                'reason': variant_entry.get('variant_reason', 'Unknown')
            })

    # Remove merged recipes
    if not dry_run:
        recipes_data['recipes'] = [r for r in recipes if r['id'] not in ids_to_delete]

    merge_log['summary'] = {
        'recipes_merged': len(merge_log['merges']),
        'recipes_deleted': len(ids_to_delete),
        'variants_linked': len(merge_log['variants_linked']),
        'errors': len(merge_log['errors'])
    }

    return recipes_data, merge_log


def main():
    parser = argparse.ArgumentParser(description='Execute recipe merges and variant links')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without modifying files')
    args = parser.parse_args()

    print("Loading data...")
    recipes_data, analysis = load_data()

    original_count = len(recipes_data.get('recipes', []))
    print(f"Original recipe count: {original_count}")

    print(f"\n{'DRY RUN - ' if args.dry_run else ''}Executing merges and variant links...")
    recipes_data, merge_log = execute_merges(recipes_data, analysis, dry_run=args.dry_run)

    # Print summary
    summary = merge_log['summary']
    print("\n" + "=" * 60)
    print("MERGE EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Recipes merged (deleted): {summary['recipes_deleted']}")
    print(f"Variants linked: {summary['variants_linked']}")
    print(f"Errors: {summary['errors']}")

    if summary['errors'] > 0:
        print("\nErrors:")
        for err in merge_log['errors'][:10]:
            print(f"  - {err}")

    new_count = len(recipes_data.get('recipes', []))
    print(f"\nRecipe count: {original_count} -> {new_count} ({original_count - new_count} removed)")

    if not args.dry_run:
        # Save updated recipes
        print("\nSaving updated recipes...")
        with open('data/recipes_master.json', 'w') as f:
            json.dump(recipes_data, f, indent=2)

        # Save merge log
        log_file = 'data/merge_log.json'
        print(f"Saving merge log to {log_file}...")
        with open(log_file, 'w') as f:
            json.dump(merge_log, f, indent=2)

        print("\nDone!")
    else:
        print("\nDry run complete. No files modified.")
        print("Run without --dry-run to apply changes.")


if __name__ == '__main__':
    main()
