#!/usr/bin/env python3
"""
Parse and normalize servings_yield strings to integer servings_count.

Examples:
  "4 servings" -> 4
  "2 dozen cookies" -> 24
  "1/2 gallon" -> 8 (cups)
  "9-inch pie" -> 8 (slices)
"""

import re
import json
from fractions import Fraction
from pathlib import Path


def parse_fraction(s: str) -> float:
    """Parse fraction string like '1/2' or '1-1/2' to float."""
    s = s.strip()
    if not s:
        return 0

    # Handle mixed fractions like "1-1/2" or "1 1/2"
    mixed_match = re.match(r'(\d+)[-\s]+(\d+)/(\d+)', s)
    if mixed_match:
        whole = int(mixed_match.group(1))
        num = int(mixed_match.group(2))
        denom = int(mixed_match.group(3))
        return whole + (num / denom)

    # Handle simple fractions like "1/2"
    if '/' in s:
        try:
            return float(Fraction(s))
        except ValueError:
            pass

    # Handle decimals and integers
    try:
        return float(s)
    except ValueError:
        return 0


def parse_range(s: str) -> float:
    """Parse range like '24-30' and return midpoint."""
    if '-' in s and not s.startswith('-'):
        parts = s.split('-')
        if len(parts) == 2:
            try:
                low = parse_fraction(parts[0])
                high = parse_fraction(parts[1])
                if low > 0 and high > 0:
                    return (low + high) / 2
            except:
                pass
    return parse_fraction(s)


# Category-based defaults when yield cannot be parsed
CATEGORY_DEFAULTS = {
    'appetizers': 8,
    'beverages': 8,
    'breads': 12,
    'breakfast': 4,
    'desserts': 12,  # average between cookies (24) and cakes (8)
    'mains': 4,
    'salads': 6,
    'sides': 6,
    'soups': 8,
    'snacks': 12,
}


def parse_yield(yield_str: str, category: str = None) -> tuple[int, str]:
    """
    Parse a yield string and return (servings_count, assumption).

    Returns:
        tuple: (servings_count as int, assumption string or None)
    """
    if not yield_str:
        default = CATEGORY_DEFAULTS.get(category, 4)
        return default, f"No yield specified, assumed {default} servings based on {category or 'default'}"

    yield_lower = yield_str.lower().strip()

    # Pattern 1: Direct servings - "4 servings", "serves 6", "6-8 servings"
    match = re.search(r'(?:serves?\s*)?(\d+(?:-\d+)?)\s*servings?', yield_lower)
    if match:
        count = int(parse_range(match.group(1)))
        return count, None

    match = re.search(r'serves?\s*(\d+(?:-\d+)?)', yield_lower)
    if match:
        count = int(parse_range(match.group(1)))
        return count, None

    # Pattern 2: Dozen - "2 dozen", "3 dozen cookies"
    match = re.search(r'(\d+(?:\.\d+)?(?:/\d+)?)\s*dozen', yield_lower)
    if match:
        dozens = parse_fraction(match.group(1))
        count = int(dozens * 12)
        return count, f"Calculated from {yield_str}"

    # Pattern 3: Specific counts - "24 cookies", "36 bars", "12 muffins"
    match = re.search(r'(\d+(?:-\d+)?)\s*(?:cookies?|bars?|brownies?|muffins?|cupcakes?|biscuits?|rolls?|pieces?|squares?|balls?|patties?)', yield_lower)
    if match:
        count = int(parse_range(match.group(1)))
        return count, None

    # Pattern 4: Cake/pie yields - "9-inch pie", "one cake", "2 layer cake"
    if re.search(r'(?:9|10|8)[\s-]*inch\s*(?:pie|cake|pan)', yield_lower):
        return 8, f"Standard 8 slices per {yield_str}"

    if re.search(r'(?:one|1|a)\s*(?:cake|pie|loaf)', yield_lower):
        return 8, "Standard 8 slices per cake/pie/loaf"

    match = re.search(r'(\d+)\s*(?:layer\s*)?(?:cakes?|pies?|loaves?)', yield_lower)
    if match:
        count = int(match.group(1)) * 8
        return count, f"Calculated {match.group(1)} x 8 slices"

    # Pattern 5: Volume yields for beverages
    match = re.search(r'(\d+(?:/\d+)?)\s*gallons?', yield_lower)
    if match:
        gallons = parse_fraction(match.group(1))
        cups = int(gallons * 16)
        return cups, f"Calculated {gallons} gallon(s) = {cups} cups (1-cup servings)"

    match = re.search(r'(\d+(?:/\d+)?)\s*quarts?', yield_lower)
    if match:
        quarts = parse_fraction(match.group(1))
        cups = int(quarts * 4)
        return cups, f"Calculated {quarts} quart(s) = {cups} cups"

    match = re.search(r'(\d+(?:/\d+)?)\s*pints?', yield_lower)
    if match:
        pints = parse_fraction(match.group(1))
        cups = int(pints * 2)
        return cups, f"Calculated {pints} pint(s) = {cups} cups"

    match = re.search(r'(\d+(?:-\d+)?)\s*cups?', yield_lower)
    if match:
        cups = int(parse_range(match.group(1)))
        return cups, f"{cups} cup servings"

    # Pattern 6: Pan-based yields
    if re.search(r'9\s*x\s*13|13\s*x\s*9', yield_lower):
        return 16, "Standard 16 pieces per 9x13 pan"

    if re.search(r'8\s*x\s*8|9\s*x\s*9', yield_lower):
        return 9, "Standard 9 pieces per 8x8/9x9 pan"

    # Pattern 7: Just a number
    match = re.match(r'^(\d+)$', yield_lower.strip())
    if match:
        return int(match.group(1)), None

    # Pattern 8: Slices
    match = re.search(r'(\d+(?:-\d+)?)\s*slices?', yield_lower)
    if match:
        count = int(parse_range(match.group(1)))
        return count, None

    # Pattern 9: Portions
    match = re.search(r'(\d+(?:-\d+)?)\s*portions?', yield_lower)
    if match:
        count = int(parse_range(match.group(1)))
        return count, None

    # Fallback to category default
    default = CATEGORY_DEFAULTS.get(category, 4)
    return default, f"Could not parse '{yield_str}', assumed {default} servings based on {category or 'default'}"


def process_recipes(input_path: str, output_path: str = None, dry_run: bool = False):
    """Process all recipes and add servings_count field."""
    with open(input_path, 'r') as f:
        data = json.load(f)

    stats = {
        'parsed_directly': 0,
        'parsed_with_assumption': 0,
        'used_default': 0,
        'already_had_count': 0,
    }

    for recipe in data['recipes']:
        # Skip if already has servings_count
        if recipe.get('servings_count'):
            stats['already_had_count'] += 1
            continue

        yield_str = recipe.get('servings_yield', '')
        category = recipe.get('category', '')

        count, assumption = parse_yield(yield_str, category)

        recipe['servings_count'] = count

        if assumption:
            if 'Could not parse' in assumption or 'No yield specified' in assumption:
                stats['used_default'] += 1
            else:
                stats['parsed_with_assumption'] += 1

            # Add to confidence flags if using default
            if 'Could not parse' in assumption or 'No yield specified' in assumption:
                if 'confidence' not in recipe:
                    recipe['confidence'] = {}
                if 'flags' not in recipe['confidence']:
                    recipe['confidence']['flags'] = []
                recipe['confidence']['flags'].append({
                    'field': 'servings_count',
                    'issue': assumption,
                    'candidates': []
                })
        else:
            stats['parsed_directly'] += 1

    print(f"\nYield Parsing Results:")
    print(f"  Parsed directly: {stats['parsed_directly']}")
    print(f"  Parsed with calculation: {stats['parsed_with_assumption']}")
    print(f"  Used category default: {stats['used_default']}")
    print(f"  Already had count: {stats['already_had_count']}")
    print(f"  Total: {len(data['recipes'])}")

    if not dry_run:
        out = output_path or input_path
        with open(out, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\nSaved to: {out}")

    return data


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Parse and normalize recipe yields')
    parser.add_argument('--input', '-i', default='data/recipes_master.json',
                        help='Input JSON file')
    parser.add_argument('--output', '-o', help='Output JSON file (default: overwrite input)')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Do not write output file')

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = Path(__file__).parent.parent / args.input

    process_recipes(str(input_path), args.output, args.dry_run)
