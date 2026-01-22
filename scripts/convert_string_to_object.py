#!/usr/bin/env python3
"""
Convert recipes with string ingredients/instructions to object format.

This script fixes schema validation errors where ingredients/instructions
are stored as plain strings instead of structured objects.

String format (bad):
  ingredients: ["1 cup flour", "2 eggs"]
  instructions: ["Mix ingredients.", "Bake at 350°F."]

Object format (correct):
  ingredients: [{"item": "flour", "quantity": "1", "unit": "cup", "prep_note": ""}]
  instructions: [{"step": 1, "text": "Mix ingredients."}]
"""

import json
import re
import sys
from pathlib import Path

# Common measurement units with variations
UNITS = {
    # Volume
    'tsp': ['tsp', 'teaspoon', 'teaspoons', 't'],
    'tbsp': ['tbsp', 'tablespoon', 'tablespoons', 'T', 'Tbsp', 'Tbs'],
    'cup': ['cup', 'cups', 'c'],
    'fl oz': ['fl oz', 'fluid ounce', 'fluid ounces'],
    'pt': ['pt', 'pint', 'pints'],
    'qt': ['qt', 'quart', 'quarts'],
    'gal': ['gal', 'gallon', 'gallons'],
    'ml': ['ml', 'milliliter', 'milliliters'],
    'L': ['L', 'liter', 'liters', 'l'],

    # Weight
    'oz': ['oz', 'ounce', 'ounces'],
    'lb': ['lb', 'lbs', 'pound', 'pounds'],
    'g': ['g', 'gram', 'grams'],
    'kg': ['kg', 'kilogram', 'kilograms'],

    # Count/Size
    'can': ['can', 'cans'],
    'jar': ['jar', 'jars'],
    'bottle': ['bottle', 'bottles'],
    'package': ['package', 'packages', 'pkg', 'pkgs'],
    'box': ['box', 'boxes'],
    'bag': ['bag', 'bags'],
    'stick': ['stick', 'sticks'],
    'slice': ['slice', 'slices'],
    'piece': ['piece', 'pieces', 'pc', 'pcs'],
    'clove': ['clove', 'cloves'],
    'head': ['head', 'heads'],
    'bunch': ['bunch', 'bunches'],
    'sprig': ['sprig', 'sprigs'],
    'stalk': ['stalk', 'stalks'],
    'ear': ['ear', 'ears'],
    'strip': ['strip', 'strips'],
    'sheet': ['sheet', 'sheets'],
    'envelope': ['envelope', 'envelopes', 'env'],
    'packet': ['packet', 'packets', 'pkt'],
    'drop': ['drop', 'drops'],
    'dash': ['dash', 'dashes'],
    'pinch': ['pinch', 'pinches'],

    # Size descriptors that act as units
    'small': ['small', 'sm'],
    'medium': ['medium', 'med'],
    'large': ['large', 'lg', 'lge'],
    'extra-large': ['extra-large', 'extra large', 'xl'],
}

# Build reverse lookup
UNIT_LOOKUP = {}
for standard, variations in UNITS.items():
    for v in variations:
        UNIT_LOOKUP[v.lower()] = standard

# Regex for quantity (fractions, decimals, ranges)
QUANTITY_PATTERN = r'^(\d+(?:/\d+)?(?:\s*-\s*\d+(?:/\d+)?)?|\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?)'

# Regex to extract prep notes in parentheses
PREP_NOTE_PATTERN = r'\(([^)]+)\)'


def parse_ingredient(ingredient_str):
    """
    Parse a string ingredient into structured format.

    Examples:
        "1 cup flour" -> {"quantity": "1", "unit": "cup", "item": "flour", "prep_note": ""}
        "2 eggs, beaten" -> {"quantity": "2", "unit": "", "item": "eggs", "prep_note": "beaten"}
        "salt and pepper to taste" -> {"quantity": "", "unit": "", "item": "salt and pepper", "prep_note": "to taste"}
    """
    if not ingredient_str or not isinstance(ingredient_str, str):
        return {"item": str(ingredient_str) if ingredient_str else "", "quantity": "", "unit": "", "prep_note": ""}

    original = ingredient_str.strip()
    text = original

    # Extract prep notes from parentheses
    prep_notes = []
    paren_matches = re.findall(PREP_NOTE_PATTERN, text)
    for match in paren_matches:
        prep_notes.append(match)
    text = re.sub(PREP_NOTE_PATTERN, '', text).strip()

    # Check for prep notes after comma
    if ',' in text:
        parts = text.split(',', 1)
        text = parts[0].strip()
        prep_notes.append(parts[1].strip())

    # Extract quantity
    quantity = ""
    qty_match = re.match(QUANTITY_PATTERN, text)
    if qty_match:
        quantity = qty_match.group(1).strip()
        text = text[qty_match.end():].strip()

    # Extract unit
    unit = ""
    words = text.split()
    if words:
        # Check first word (and possibly second for compound units like "fl oz")
        first_word = words[0].lower().rstrip('.,;')

        # Check for compound unit
        if len(words) > 1:
            compound = f"{first_word} {words[1].lower().rstrip('.,;')}"
            if compound in UNIT_LOOKUP:
                unit = UNIT_LOOKUP[compound]
                text = ' '.join(words[2:])
            elif first_word in UNIT_LOOKUP:
                unit = UNIT_LOOKUP[first_word]
                text = ' '.join(words[1:])
        elif first_word in UNIT_LOOKUP:
            unit = UNIT_LOOKUP[first_word]
            text = ' '.join(words[1:])

    # Handle size descriptors with parenthetical content like "1 (3 oz) package"
    size_match = re.match(r'^\(([^)]+)\)\s*', text)
    if size_match:
        # Move size info to prep note
        prep_notes.insert(0, size_match.group(1))
        text = text[size_match.end():].strip()

        # Check if next word is a unit
        remaining_words = text.split()
        if remaining_words:
            next_word = remaining_words[0].lower().rstrip('.,;')
            if next_word in UNIT_LOOKUP:
                unit = UNIT_LOOKUP[next_word]
                text = ' '.join(remaining_words[1:])

    # Clean up the item name
    item = text.strip()
    # Remove leading "of" (e.g., "1 cup of flour" -> "flour")
    if item.lower().startswith('of '):
        item = item[3:].strip()

    # Combine prep notes
    prep_note = '; '.join(prep_notes) if prep_notes else ""

    return {
        "item": item,
        "quantity": quantity,
        "unit": unit,
        "prep_note": prep_note
    }


def parse_instruction(instruction_str, step_num):
    """
    Convert a string instruction to object format.

    Examples:
        "Mix ingredients." -> {"step": 1, "text": "Mix ingredients."}
    """
    if not instruction_str or not isinstance(instruction_str, str):
        return {"step": step_num, "text": str(instruction_str) if instruction_str else ""}

    return {
        "step": step_num,
        "text": instruction_str.strip()
    }


def convert_recipe(recipe):
    """
    Convert a recipe's ingredients and instructions to object format if needed.
    Returns True if conversion was performed, False otherwise.
    """
    converted = False

    # Convert ingredients
    if recipe.get('ingredients'):
        if recipe['ingredients'] and isinstance(recipe['ingredients'][0], str):
            recipe['ingredients'] = [
                parse_ingredient(ing) for ing in recipe['ingredients']
            ]
            converted = True

    # Convert instructions
    if recipe.get('instructions'):
        if recipe['instructions'] and isinstance(recipe['instructions'][0], str):
            recipe['instructions'] = [
                parse_instruction(inst, i + 1)
                for i, inst in enumerate(recipe['instructions'])
            ]
            converted = True

    return converted


def main():
    master_file = Path('data/recipes_master.json')

    if not master_file.exists():
        print(f"Error: {master_file} not found")
        sys.exit(1)

    # Load recipes
    with open(master_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Track conversions
    converted_count = 0
    converted_recipes = []

    for recipe in data['recipes']:
        if convert_recipe(recipe):
            converted_count += 1
            converted_recipes.append(recipe['id'])

    if converted_count == 0:
        print("No recipes needed conversion. All recipes already in object format.")
        return

    # Save updated file
    with open(master_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Converted {converted_count} recipes from string to object format.")
    print(f"\nConverted recipes:")
    for rid in converted_recipes[:20]:
        print(f"  - {rid}")
    if len(converted_recipes) > 20:
        print(f"  ... and {len(converted_recipes) - 20} more")


if __name__ == '__main__':
    main()
