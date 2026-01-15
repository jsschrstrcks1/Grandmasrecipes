#!/usr/bin/env python3
"""
Duplicate and Variant Analysis Script

Analyzes recipes to find:
1. True duplicates (merge candidates)
2. Variants (similar recipes with meaningful differences)
3. Source priority violations

Source Priority Order:
1. grandma-baker / handwritten
2. mommom-baker
3. granny-hudson
4. bhg
5. all others
"""

import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

# Source priority (lower = higher priority)
SOURCE_PRIORITY = {
    'grandma-baker': 1,
    'handwritten': 1,
    'mommom-baker': 2,
    'granny-hudson': 3,
    'bhg': 4,
}
DEFAULT_PRIORITY = 99

# Categories to skip (not actual recipes)
SKIP_CATEGORIES = ['tips', 'reference']


def get_source_priority(recipe):
    """Get priority score for a recipe based on its source."""
    collection = recipe.get('collection', '').lower()
    recipe_id = recipe.get('id', '').lower()

    # Check collection first
    if collection in SOURCE_PRIORITY:
        return SOURCE_PRIORITY[collection]

    # Check if ID contains source hints
    for source, priority in SOURCE_PRIORITY.items():
        if source in recipe_id:
            return priority

    # Check source field if present
    source = recipe.get('source', '').lower()
    for src, priority in SOURCE_PRIORITY.items():
        if src in source:
            return priority

    return DEFAULT_PRIORITY


def get_source_name(recipe):
    """Get human-readable source name."""
    collection = recipe.get('collection', '')
    if collection:
        return collection

    recipe_id = recipe.get('id', '')
    for source in SOURCE_PRIORITY.keys():
        if source in recipe_id.lower():
            return source

    return recipe.get('source', 'unknown')


def normalize_title(title):
    """Normalize title for comparison."""
    if not title:
        return ''

    # Lowercase
    normalized = title.lower()

    # Remove common suffixes
    suffixes = [
        r'-bhg(-\d+)?$', r'-handwritten(-\d+)?$', r'-mommom(-\d+)?$',
        r'-granny(-\d+)?$', r'-grandma(-\d+)?$', r'-family(-\d+)?$',
        r'-variant(-\d+)?$', r'-homemade$', r'-classic$', r'-recipe$',
        r'-womans-day$', r'-themetropo$', r'-food-com$', r'-allrecipes$',
        r'-\d+$'  # trailing numbers
    ]
    for suffix in suffixes:
        normalized = re.sub(suffix, '', normalized)

    # Remove punctuation except hyphens
    normalized = re.sub(r'[^\w\s-]', '', normalized)

    # Normalize whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    # Replace spaces with hyphens for consistency
    normalized = normalized.replace(' ', '-')

    return normalized


def normalize_quantity(qty):
    """Normalize quantity string to handle fraction variations."""
    if not qty:
        return ''

    qty = str(qty).strip()

    # Unicode fraction map
    unicode_fractions = {
        '½': '1/2', '⅓': '1/3', '⅔': '2/3', '¼': '1/4', '¾': '3/4',
        '⅕': '1/5', '⅖': '2/5', '⅗': '3/5', '⅘': '4/5',
        '⅙': '1/6', '⅚': '5/6', '⅛': '1/8', '⅜': '3/8', '⅝': '5/8', '⅞': '7/8',
    }
    for uni, ascii_frac in unicode_fractions.items():
        qty = qty.replace(uni, ascii_frac)

    # Decimal to fraction conversion for common values
    decimal_map = {
        '0.25': '1/4', '0.5': '1/2', '0.75': '3/4',
        '0.33': '1/3', '0.67': '2/3',
        '1.5': '1 1/2', '1.25': '1 1/4', '1.75': '1 3/4',
        '2.5': '2 1/2', '2.25': '2 1/4', '2.75': '2 3/4',
    }
    for dec, frac in decimal_map.items():
        if qty == dec:
            qty = frac

    # Normalize "1 to 2" / "1-2" variations
    qty = re.sub(r'(\d+)\s*to\s*(\d+)', r'\1-\2', qty)
    qty = re.sub(r'(\d+)\s*-\s*(\d+)', r'\1-\2', qty)

    # Normalize "1-3/4" to "1 3/4"
    qty = re.sub(r'(\d+)-(\d+/\d+)', r'\1 \2', qty)

    return qty.lower()


def normalize_ingredient(ing):
    """Normalize an ingredient for comparison."""
    item = ing.get('item', '').lower().strip()
    qty = normalize_quantity(ing.get('quantity', ''))
    unit = ing.get('unit', '').lower().strip()

    # Normalize common variations in item names
    item = re.sub(r'\s+', ' ', item)
    item = item.replace('all-purpose ', '').replace('all purpose ', '')

    # Standardize units
    unit_map = {
        'tablespoon': 'tbsp', 'tablespoons': 'tbsp',
        'teaspoon': 'tsp', 'teaspoons': 'tsp',
        'cups': 'cup', 'ounces': 'oz', 'ounce': 'oz',
        'pounds': 'lb', 'pound': 'lb',
    }
    unit = unit_map.get(unit, unit)

    return (item, qty, unit)


def get_ingredient_set(recipe):
    """Get normalized set of ingredients."""
    ingredients = recipe.get('ingredients', [])
    if not ingredients:
        return set()

    normalized = set()
    for ing in ingredients:
        if isinstance(ing, dict):
            norm = normalize_ingredient(ing)
            if norm[0]:  # Has item name
                normalized.add(norm)

    return normalized


def get_ingredient_items_only(recipe):
    """Get just ingredient items (without quantities) for looser matching."""
    ingredients = recipe.get('ingredients', [])
    if not ingredients:
        return set()

    items = set()
    for ing in ingredients:
        if isinstance(ing, dict):
            item = ing.get('item', '').lower().strip()
            if item:
                # Normalize common variations
                item = re.sub(r'\s+', ' ', item)
                items.add(item)

    return items


def normalize_instruction(text):
    """Normalize instruction text for comparison."""
    if not text:
        return ''

    text = text.lower()

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Normalize common variations
    replacements = [
        (r'\bmix well\b', 'stir'),
        (r'\bstir thoroughly\b', 'stir'),
        (r'\bcombine\b', 'mix'),
        (r'\bblend\b', 'mix'),
        (r'\bpreheat\b', 'heat'),
        (r'\bapprox\.?\b', 'about'),
        (r'\bapproximately\b', 'about'),
        (r'\bminutes?\b', 'min'),
        (r'\bhours?\b', 'hr'),
        (r'\bdegrees?\b', '°'),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)

    return text


def get_instruction_text(recipe):
    """Get combined normalized instruction text."""
    instructions = recipe.get('instructions', [])
    if not instructions:
        return ''

    texts = []
    for inst in instructions:
        if isinstance(inst, dict):
            text = inst.get('text', '')
        else:
            text = str(inst)
        if text:
            texts.append(normalize_instruction(text))

    return ' '.join(texts)


def similarity_ratio(a, b):
    """Calculate similarity ratio between two strings."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def ingredient_similarity(recipe1, recipe2):
    """Calculate ingredient similarity between two recipes."""
    set1 = get_ingredient_set(recipe1)
    set2 = get_ingredient_set(recipe2)

    if not set1 or not set2:
        return 0.0, 0.0

    # Exact match (item + qty + unit)
    exact_overlap = set1 & set2
    exact_score = len(exact_overlap) / max(len(set1), len(set2))

    # Item-only match (ignoring quantities)
    items1 = get_ingredient_items_only(recipe1)
    items2 = get_ingredient_items_only(recipe2)
    item_overlap = items1 & items2
    item_score = len(item_overlap) / max(len(items1), len(items2)) if items1 and items2 else 0.0

    return exact_score, item_score


def instruction_similarity(recipe1, recipe2):
    """Calculate instruction similarity between two recipes."""
    text1 = get_instruction_text(recipe1)
    text2 = get_instruction_text(recipe2)

    return similarity_ratio(text1, text2)


def classify_pair(recipe1, recipe2):
    """
    Classify a pair of recipes.

    Returns:
        'merge': Same spirit, can be merged (maintain provenance)
        'variant': Similar but meaningful differences (link as variant)
        'different': Not related enough to link
    """
    exact_ing, item_ing = ingredient_similarity(recipe1, recipe2)
    inst_sim = instruction_similarity(recipe1, recipe2)

    same_source = get_source_name(recipe1) == get_source_name(recipe2)

    scores = {
        'exact_ingredient_match': exact_ing,
        'item_ingredient_match': item_ing,
        'instruction_similarity': inst_sim,
        'same_source': same_source
    }

    # MERGE candidates: essentially the same recipe
    # Case 1: Same items, same instructions (transcription variations)
    if item_ing >= 0.95 and inst_sim >= 0.90:
        scores['reason'] = 'Near-identical recipe (transcription variation)'
        return 'merge', scores

    # Case 2: Same source + high item match + high instruction match
    # (likely duplicate import with minor OCR differences)
    if same_source and item_ing >= 0.85 and inst_sim >= 0.85:
        scores['reason'] = 'Same source duplicate (OCR/import variation)'
        return 'merge', scores

    # Case 3: Very high exact match (quantities too)
    if exact_ing >= 0.90 and inst_sim >= 0.70:
        scores['reason'] = 'High ingredient and instruction match'
        return 'merge', scores

    # VARIANT candidates: same dish, meaningful differences
    # Case 1: Same ingredients, different quantities
    if item_ing >= 0.80 and exact_ing < 0.85:
        scores['reason'] = 'Same ingredients, different quantities'
        return 'variant', scores

    # Case 2: Similar ingredients + very similar instructions
    if item_ing >= 0.70 and inst_sim >= 0.80:
        scores['reason'] = 'Similar recipe with variations'
        return 'variant', scores

    # Case 3: Different sources with moderate similarity (cross-family variants)
    if not same_source and item_ing >= 0.60 and inst_sim >= 0.60:
        scores['reason'] = 'Cross-source variant'
        return 'variant', scores

    # Not related enough
    scores['reason'] = 'Insufficient similarity'
    return 'different', scores


def analyze_recipes(recipes_file):
    """Main analysis function."""
    with open(recipes_file) as f:
        data = json.load(f)

    recipes = data.get('recipes', [])
    print(f"Loaded {len(recipes)} recipes")

    # Filter out tips/reference
    actual_recipes = [r for r in recipes if r.get('category') not in SKIP_CATEGORIES]
    print(f"Analyzing {len(actual_recipes)} actual recipes (excluding tips/reference)")

    # Group by normalized title
    title_groups = defaultdict(list)
    for recipe in actual_recipes:
        title = recipe.get('title', '')
        norm_title = normalize_title(title)
        if norm_title:
            title_groups[norm_title].append(recipe)

    # Find groups with multiple recipes
    multi_groups = {k: v for k, v in title_groups.items() if len(v) > 1}
    print(f"Found {len(multi_groups)} title groups with potential duplicates/variants")

    # Analyze each group comprehensively
    recipe_groups = []

    for norm_title, group in multi_groups.items():
        # Sort by priority
        group_sorted = sorted(group, key=lambda r: (get_source_priority(r), r.get('id', '')))

        canonical = group_sorted[0]
        canonical_priority = get_source_priority(canonical)

        group_analysis = {
            'normalized_title': norm_title,
            'canonical': {
                'id': canonical.get('id'),
                'title': canonical.get('title'),
                'source': get_source_name(canonical),
                'priority': canonical_priority
            },
            'merge_into_canonical': [],
            'keep_as_variants': [],
            'total_in_group': len(group)
        }

        for other in group_sorted[1:]:
            classification, scores = classify_pair(canonical, other)

            entry = {
                'id': other.get('id'),
                'title': other.get('title'),
                'source': get_source_name(other),
                'priority': get_source_priority(other),
                'scores': scores
            }

            if classification == 'merge':
                group_analysis['merge_into_canonical'].append(entry)
            elif classification == 'variant':
                entry['variant_reason'] = scores.get('reason', 'Similar recipe')
                group_analysis['keep_as_variants'].append(entry)

        recipe_groups.append(group_analysis)

    # Separate into actionable categories
    merge_groups = [g for g in recipe_groups if g['merge_into_canonical']]
    variant_groups = [g for g in recipe_groups if g['keep_as_variants'] and not g['merge_into_canonical']]
    mixed_groups = [g for g in recipe_groups if g['merge_into_canonical'] and g['keep_as_variants']]

    # Count totals
    total_merge = sum(len(g['merge_into_canonical']) for g in recipe_groups)
    total_variant = sum(len(g['keep_as_variants']) for g in recipe_groups)

    return {
        'summary': {
            'total_recipes': len(actual_recipes),
            'title_groups_analyzed': len(multi_groups),
            'groups_with_merges': len(merge_groups),
            'groups_with_variants_only': len(variant_groups),
            'groups_with_both': len(mixed_groups),
            'total_recipes_to_merge': total_merge,
            'total_variants_to_link': total_variant
        },
        'recipe_groups': recipe_groups,
        'merge_groups': merge_groups,
        'variant_groups': variant_groups,
        'mixed_groups': mixed_groups
    }


def print_report(analysis):
    """Print a human-readable report."""
    summary = analysis['summary']

    print("\n" + "=" * 70)
    print("DUPLICATE & VARIANT ANALYSIS REPORT")
    print("=" * 70)

    print(f"\nTotal recipes analyzed: {summary['total_recipes']}")
    print(f"Title groups analyzed: {summary['title_groups_analyzed']}")

    print(f"\n📊 SUMMARY:")
    print(f"   Groups with merges only: {summary['groups_with_merges'] - summary['groups_with_both']}")
    print(f"   Groups with variants only: {summary['groups_with_variants_only']}")
    print(f"   Groups with both merges & variants: {summary['groups_with_both']}")
    print(f"\n   Total recipes to merge: {summary['total_recipes_to_merge']}")
    print(f"   Total variants to link: {summary['total_variants_to_link']}")

    # Sample merge groups
    merge_groups = analysis.get('merge_groups', [])
    if merge_groups:
        print("\n" + "-" * 70)
        print("SAMPLE MERGE GROUPS (first 15)")
        print("-" * 70)
        for group in merge_groups[:15]:
            canonical = group['canonical']
            print(f"\n  KEEP: {canonical['id']} ({canonical['source']})")
            for m in group['merge_into_canonical']:
                scores = m['scores']
                print(f"    MERGE: {m['id']} ({m['source']})")
                print(f"           Items: {scores['item_ingredient_match']:.0%}, Instr: {scores['instruction_similarity']:.0%}")
                print(f"           Reason: {scores.get('reason', '')}")

    # Sample variant groups
    variant_groups = analysis.get('variant_groups', [])
    if variant_groups:
        print("\n" + "-" * 70)
        print("SAMPLE VARIANT-ONLY GROUPS (first 15)")
        print("-" * 70)
        for group in variant_groups[:15]:
            canonical = group['canonical']
            print(f"\n  CANONICAL: {canonical['id']} ({canonical['source']})")
            for v in group['keep_as_variants']:
                scores = v['scores']
                print(f"    VARIANT: {v['id']} ({v['source']})")
                print(f"             Items: {scores['item_ingredient_match']:.0%}, Exact: {scores['exact_ingredient_match']:.0%}")
                print(f"             Reason: {v.get('variant_reason', '')}")

    # Mixed groups (both merges and variants)
    mixed_groups = analysis.get('mixed_groups', [])
    if mixed_groups:
        print("\n" + "-" * 70)
        print("SAMPLE MIXED GROUPS - merges AND variants (first 10)")
        print("-" * 70)
        for group in mixed_groups[:10]:
            canonical = group['canonical']
            print(f"\n  CANONICAL: {canonical['id']} ({canonical['source']})")
            for m in group['merge_into_canonical']:
                print(f"    MERGE: {m['id']} ({m['source']})")
            for v in group['keep_as_variants']:
                print(f"    VARIANT: {v['id']} - {v.get('variant_reason', '')}")


def main():
    import sys

    recipes_file = Path('data/recipes_master.json')
    if not recipes_file.exists():
        print(f"Error: {recipes_file} not found")
        sys.exit(1)

    print("Analyzing recipes for duplicates and variants...")
    analysis = analyze_recipes(recipes_file)

    # Print report
    print_report(analysis)

    # Save full report
    report_file = Path('data/duplicate_analysis.json')
    with open(report_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    print(f"\nFull report saved to: {report_file}")


if __name__ == '__main__':
    main()
