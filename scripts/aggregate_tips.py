#!/usr/bin/env python3
"""
Aggregate Kitchen Tips from Family Repositories

Fetches tips from all family recipe repositories and merges them into
the hub's kitchen-tips.json for unified display.

Usage:
    python scripts/aggregate_tips.py           # Full aggregation
    python scripts/aggregate_tips.py --dry-run # Preview without saving

Remote Sources:
    - MomsRecipes: data/tips.json (113 tips)
    - Allrecipes: data/tips_master.json (27 tips)
"""

import json
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# Remote tips sources
REMOTE_TIPS = {
    'mommom-baker': {
        'url': 'https://jsschrstrcks1.github.io/MomsRecipes/data/tips.json',
        'display_name': 'MomMom Baker',
        'format': 'moms'  # {tips: [{id, category, title, tip, source}]}
    },
    'all': {
        'url': 'https://jsschrstrcks1.github.io/Allrecipes/data/tips_master.json',
        'display_name': 'Other Recipes',
        'format': 'allrecipes'  # [{id, title, content, category, related_ingredients, ...}]
    }
}

# Category mapping to standardize across sources
CATEGORY_MAP = {
    # MomsRecipes categories
    'baking': 'baking-general',
    'microwave': 'microwave',
    'bread machine': 'bread-machine',
    'storage': 'storage',
    'seafood': 'seafood',
    'candy': 'candy-making',
    'cookies': 'baking-cookies',
    'freezing': 'storage',
    'meat': 'meat-cooking',
    'turkey': 'meat-cooking',
    'eggs': 'eggs',
    'pasta': 'pasta',
    'vegetables': 'vegetables',
    'sauce': 'sauces',
    'general': 'general',
    # Allrecipes categories
    'selection': 'selection',
    'preparation': 'preparation',
    'cooking': 'cooking',
    'substitution': 'substitution',
    'technique': 'technique',
    'equipment': 'equipment',
    'safety': 'safety',
    'serving': 'serving',
}


def fetch_remote_tips(url: str, timeout: int = 30) -> Tuple[List[Dict], Optional[str]]:
    """Fetch tips from a remote URL."""
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'GrandmasRecipes-TipsAggregator/1.0'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode('utf-8'))

            # Handle different formats
            if isinstance(data, dict) and 'tips' in data:
                return data['tips'], None
            elif isinstance(data, list):
                return data, None
            else:
                return [], f"Unexpected format: {type(data)}"

    except urllib.error.URLError as e:
        return [], f"URL error: {e.reason}"
    except urllib.error.HTTPError as e:
        return [], f"HTTP {e.code}: {e.reason}"
    except json.JSONDecodeError as e:
        return [], f"JSON error: {e}"
    except Exception as e:
        return [], f"Error: {e}"


def normalize_moms_tip(tip: Dict, collection: str) -> Dict:
    """Normalize MomsRecipes tip format."""
    category = tip.get('category', 'general').lower()
    return {
        'id': tip.get('id', ''),
        'text': tip.get('tip', ''),
        'title': tip.get('title', ''),
        'category': CATEGORY_MAP.get(category, category),
        'attribution': tip.get('source', 'MomMom Baker'),
        'collection': collection,
        'relatedRecipes': [],
        'relatedIngredients': [],
        'searchTerms': []
    }


def normalize_allrecipes_tip(tip: Dict, collection: str) -> Dict:
    """Normalize Allrecipes tip format."""
    category = tip.get('category', 'general').lower()
    return {
        'id': tip.get('id', ''),
        'text': tip.get('content', ''),
        'title': tip.get('title', ''),
        'category': CATEGORY_MAP.get(category, category),
        'attribution': tip.get('source_note', 'Family cooking wisdom'),
        'collection': collection,
        'relatedRecipes': [],
        'relatedIngredients': tip.get('related_ingredients', []),
        'searchTerms': tip.get('search_terms', []),
        'relatedTags': tip.get('related_tags', [])
    }


def load_local_tips(tips_path: Path) -> Dict:
    """Load local kitchen-tips.json."""
    if not tips_path.exists():
        return {'version': '1.0.0', 'categories': []}

    with open(tips_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_local_tips(local_data: Dict) -> List[Dict]:
    """Extract tips from local category-based format."""
    tips = []
    for category in local_data.get('categories', []):
        cat_id = category.get('id', 'general')
        cat_name = category.get('name', 'General')
        for tip in category.get('tips', []):
            tips.append({
                'id': f"{cat_id}-{len(tips)}",
                'text': tip.get('text', ''),
                'title': '',
                'category': cat_id,
                'categoryName': cat_name,
                'categoryIcon': category.get('icon', '👩‍🍳'),
                'attribution': tip.get('attribution', 'Grandma Baker'),
                'collection': tip.get('collection', 'grandma-baker'),
                'relatedRecipes': tip.get('relatedRecipes', []),
                'relatedIngredients': [],
                'searchTerms': []
            })
    return tips


def merge_tips(local_tips: List[Dict], remote_tips: Dict[str, List[Dict]]) -> List[Dict]:
    """Merge local and remote tips, avoiding exact duplicates."""
    # Use text content as signature for deduplication
    seen_signatures = {tip['text'].lower().strip()[:100] for tip in local_tips if tip.get('text')}

    merged = list(local_tips)

    for collection_id, tips in remote_tips.items():
        for tip in tips:
            sig = tip.get('text', '').lower().strip()[:100]
            if sig and sig not in seen_signatures:
                merged.append(tip)
                seen_signatures.add(sig)

    return merged


def rebuild_category_format(tips: List[Dict]) -> Dict:
    """Rebuild the category-based format for kitchen-tips.json."""
    # Group tips by category
    by_category = {}
    for tip in tips:
        cat = tip.get('category', 'general')
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(tip)

    # Category metadata
    category_meta = {
        'candy-making': {'name': 'Candy Making', 'icon': '🍬'},
        'baking-bread': {'name': 'Bread Baking', 'icon': '🍞'},
        'baking-cakes': {'name': 'Cake Baking', 'icon': '🎂'},
        'baking-cookies': {'name': 'Cookie Baking', 'icon': '🍪'},
        'baking-pies': {'name': 'Pie Making', 'icon': '🥧'},
        'baking-general': {'name': 'Baking Tips', 'icon': '🧁'},
        'meat-cooking': {'name': 'Meat Cooking', 'icon': '🥩'},
        'eggs': {'name': 'Egg Cookery', 'icon': '🥚'},
        'sauces': {'name': 'Sauces & Gravies', 'icon': '🥣'},
        'vegetables': {'name': 'Vegetables', 'icon': '🥕'},
        'soups-stews': {'name': 'Soups & Stews', 'icon': '🍲'},
        'frying': {'name': 'Frying', 'icon': '🍳'},
        'general': {'name': 'General Cooking', 'icon': '👩‍🍳'},
        'microwave': {'name': 'Microwave Cooking', 'icon': '📡'},
        'bread-machine': {'name': 'Bread Machine', 'icon': '🍞'},
        'storage': {'name': 'Storage & Freezing', 'icon': '❄️'},
        'seafood': {'name': 'Seafood', 'icon': '🐟'},
        'pasta': {'name': 'Pasta', 'icon': '🍝'},
        'selection': {'name': 'Ingredient Selection', 'icon': '🛒'},
        'preparation': {'name': 'Preparation', 'icon': '🔪'},
        'cooking': {'name': 'Cooking Techniques', 'icon': '🍳'},
        'substitution': {'name': 'Substitutions', 'icon': '🔄'},
        'technique': {'name': 'Techniques', 'icon': '📝'},
        'equipment': {'name': 'Equipment', 'icon': '🍳'},
        'safety': {'name': 'Food Safety', 'icon': '⚠️'},
        'serving': {'name': 'Serving', 'icon': '🍽️'},
    }

    # Build categories array
    categories = []
    for cat_id, cat_tips in sorted(by_category.items()):
        meta = category_meta.get(cat_id, {'name': cat_id.title(), 'icon': '💡'})
        categories.append({
            'id': cat_id,
            'name': meta['name'],
            'icon': meta['icon'],
            'tips': [
                {
                    'text': t['text'],
                    'attribution': t.get('attribution', 'Family wisdom'),
                    'collection': t.get('collection', 'grandma-baker'),
                    'relatedRecipes': t.get('relatedRecipes', []),
                    'relatedIngredients': t.get('relatedIngredients', [])
                }
                for t in cat_tips
            ]
        })

    return {
        'version': '2.0.0',
        'description': 'Family kitchen wisdom aggregated from all collections',
        'last_updated': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'categories': categories
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Aggregate kitchen tips from family repositories')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Preview without saving')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')

    args = parser.parse_args()

    # Paths
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    tips_path = project_dir / 'data' / 'kitchen-tips.json'

    print("=" * 60)
    print("KITCHEN TIPS AGGREGATOR")
    print("=" * 60)
    print()

    # Load local tips
    print(f"Loading local tips from {tips_path}...")
    local_data = load_local_tips(tips_path)
    local_tips = extract_local_tips(local_data)
    print(f"  Local tips: {len(local_tips)}")

    # Fetch remote tips
    remote_tips = {}
    print()
    print("Fetching remote tips...")

    for collection_id, config in REMOTE_TIPS.items():
        print(f"  {config['display_name']} ({collection_id})...")
        print(f"    URL: {config['url']}")

        tips, error = fetch_remote_tips(config['url'])

        if error:
            print(f"    ERROR: {error}")
            continue

        # Normalize tips based on format
        normalized = []
        for tip in tips:
            if config['format'] == 'moms':
                normalized.append(normalize_moms_tip(tip, collection_id))
            else:
                normalized.append(normalize_allrecipes_tip(tip, collection_id))

        remote_tips[collection_id] = normalized
        print(f"    Fetched: {len(normalized)} tips")

    # Merge tips
    print()
    print("Merging tips...")
    merged = merge_tips(local_tips, remote_tips)
    print(f"  Total merged: {len(merged)} tips")

    # Rebuild category format
    output_data = rebuild_category_format(merged)

    # Count by category
    print()
    print("Tips by category:")
    for cat in output_data['categories']:
        print(f"  {cat['icon']} {cat['name']}: {len(cat['tips'])}")

    if args.dry_run:
        print()
        print("DRY RUN - No changes saved")
    else:
        print()
        print(f"Saving to {tips_path}...")
        with open(tips_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print("  Done!")

    print()
    print("=" * 60)
    print(f"SUMMARY: {len(merged)} total tips")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
