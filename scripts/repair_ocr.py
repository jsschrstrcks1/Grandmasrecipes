#!/usr/bin/env python3
"""
OCR Repair Script for corrupted recipes.

Fixes common OCR corruption patterns:
1. Merged words (e.g., "Boilsugar" -> "Boil sugar")
2. Missing spaces (e.g., "andthe" -> "and the")
3. Corrupted fractions (e.g., "V2" -> "1/2", "14" -> "1/4")
4. Strange characters (e.g., "%" -> "1/2")
"""

import json
import re
from pathlib import Path


def fix_merged_words(text):
    """Fix common merged word patterns."""
    if not text:
        return text

    # First pass: lowercase patterns with word boundaries
    lowercase_patterns = [
        # Common merged prepositions/articles - case insensitive
        (r'(\w)(of)(the|a|an|this|that|some|all|each|one|two|three|four|five|six|seven|eight|egg|cup|teaspoon|tablespoon|milk|sugar|flour|water|butter|salt|pepper|cream|onion|pan|bowl|dish|sauce)', r'\1 of \3'),
        (r'(\w)(the)(egg|milk|sugar|flour|water|butter|salt|pepper|cream|onion|pan|bowl|dish|sauce|mixture|bread|meat|rice|potatoes|chicken|fish|beef|yolk|white|batter|dough|oven|fire|heat|cold|hot|top|bottom|rest|center|middle)', r'\1 the \3'),
        (r'(\w)(and)(add|the|mix|stir|pour|cook|bake|fry|boil|let|set|put|cut|chop|grate|beat|fold|blend|serve|remove|drain|cover)', r'\1 and \3'),
        (r'(\w)(with)(the|a|an|hot|cold|warm|boiling|melted|beaten|chopped|grated|sliced|some|little|milk|water|butter|cream|salt|pepper)', r'\1 with \3'),
        (r'(\w)(into)(the|a|an|pan|bowl|dish|pot|mixture|batter|dough)', r'\1 into \3'),
        (r'(\w)(until)(smooth|thick|brown|golden|done|tender|soft|firm|set|cooked)', r'\1 until \3'),
        (r'(\w)(to)(the|a|taste|cool|boil|simmer)', r'\1 to \3'),
        (r'(\w)(in)(the|a|an|pan|bowl|dish|pot|oven|half)', r'\1 in \3'),
        (r'(\w)(on)(the|a|top|fire|heat|plate|dish)', r'\1 on \3'),
        (r'(\w)(or)(the|a|until|more)', r'\1 or \3'),
    ]

    for pattern, replacement in lowercase_patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Second pass: specific common merged words
    specific_fixes = [
        # Verb + following word
        (r'\bBoilsugar\b', 'Boil sugar'),
        (r'\bAddthe\b', 'Add the'),
        (r'\bPutthe\b', 'Put the'),
        (r'\bMixthe\b', 'Mix the'),
        (r'\bCutthe\b', 'Cut the'),
        (r'\bMeltthe\b', 'Melt the'),
        (r'\bStirthe\b', 'Stir the'),
        (r'\bDrainthe\b', 'Drain the'),
        (r'\bPourthe\b', 'Pour the'),
        (r'\bRinsethe\b', 'Rinse the'),
        (r'\bServethe\b', 'Serve the'),
        (r'\bRemovethe\b', 'Remove the'),
        (r'\bPlacethe\b', 'Place the'),
        (r'\bWashthe\b', 'Wash the'),
        (r'\bBeatthe\b', 'Beat the'),
        (r'\bFrythe\b', 'Fry the'),
        (r'\bBakethe\b', 'Bake the'),

        # Common compound words that got merged
        (r'\bdrippotwith\b', 'drip pot with'),
        (r'\bdripbag\b', 'drip bag'),
        (r'\bhotwater\b', 'hot water'),
        (r'\bcoldwater\b', 'cold water'),
        (r'\bboilingwater\b', 'boiling water'),
        (r'\bsetaside\b', 'set aside'),
        (r'\btocool\b', 'to cool'),
        (r'\bslowly\b', 'slowly'),  # this is correct, skip

        # Word + preposition merged
        (r'(\w{3,})ofthe\b', r'\1 of the'),
        (r'(\w{3,})andthe\b', r'\1 and the'),
        (r'(\w{3,})tothe\b', r'\1 to the'),
        (r'(\w{3,})inthe\b', r'\1 in the'),
        (r'(\w{3,})onthe\b', r'\1 on the'),
        (r'(\w{3,})withthe\b', r'\1 with the'),
        (r'(\w{3,})intothe\b', r'\1 into the'),
        (r'(\w{3,})fromthe\b', r'\1 from the'),
        (r'(\w{3,})overthe\b', r'\1 over the'),
        (r'(\w{3,})thru\b', r'\1 thru'),

        # Measurements
        (r'(\d+)\s*cupmilk\b', r'\1 cup milk'),
        (r'(\d+)\s*cupsmilk\b', r'\1 cups milk'),
        (r'(\d+)\s*cupsugar\b', r'\1 cup sugar'),
        (r'(\d+)\s*cupssugar\b', r'\1 cups sugar'),
        (r'(\d+)\s*cupflour\b', r'\1 cup flour'),
        (r'(\d+)\s*cupsflour\b', r'\1 cups flour'),
        (r'(\d+)\s*cupwater\b', r'\1 cup water'),
        (r'(\d+)\s*cupswater\b', r'\1 cups water'),
    ]

    for pattern, replacement in specific_fixes:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Third pass: camelCase splitting (lowercase followed by uppercase)
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

    return text


def fix_fractions(text):
    """Fix corrupted fraction representations."""
    if not text:
        return text

    # Common OCR fraction errors
    replacements = [
        # V or v mistaken for 1/
        (r'\bV\s*2\b', '1/2'),
        (r'\bv\s*2\b', '1/2'),
        (r'\bV2\b', '1/2'),
        (r'\bv2\b', '1/2'),

        # i/ mistaken for 1/
        (r'\bi/2\b', '1/2'),
        (r'\bi/4\b', '1/4'),
        (r'\bi/3\b', '1/3'),

        # y mistaken for 1/
        (r'\by\s*2\b', '1/2'),
        (r'\by2\b', '1/2'),

        # % mistaken for 1/2
        (r'%\s*teaspoon', '1/2 teaspoon'),
        (r'%\s*tablespoon', '1/2 tablespoon'),
        (r'%\s*cup', '1/2 cup'),

        # ^ mistaken for 1/2
        (r'\^\s*teaspoon', '1/2 teaspoon'),
        (r'\^\s*tablespoon', '1/2 tablespoon'),
        (r'\^\s*cup', '1/2 cup'),

        # 14 or 14. mistaken for 1/4
        (r'\b14\.?\s*teaspoon', '1/4 teaspoon'),
        (r'\b14\.?\s*cup', '1/4 cup'),

        # 1^ mistaken for 1/2 or 1 1/2
        (r'1\^', '1 1/2'),
        (r'1/\^', '1/2'),

        # .2 at start (OCR of 1/2)
        (r'^\.2\s', '1/2 '),

        # Standalone numbers that are likely fractions in context
        (r'\b12\s+(teaspoon|tablespoon)', r'1/2 \1'),
        (r'\b34\s+(cup|teaspoon)', r'3/4 \1'),

        # 1% meaning 1 1/2
        (r'1%\s*(cup|teaspoon|tablespoon)', r'1 1/2 \1'),

        # Numbers with periods that should be fractions
        (r'(\d+)\.(\d+)\s*(cup|teaspoon|tablespoon)', lambda m: f"{m.group(1)} {int(m.group(2))/10 if len(m.group(2)) == 1 else m.group(2)} {m.group(3)}"),
    ]

    for pattern, replacement in replacements:
        if callable(replacement):
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        else:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text


def fix_punctuation_spacing(text):
    """Fix spacing around punctuation."""
    if not text:
        return text

    # Add space after periods if followed by letter
    text = re.sub(r'\.([A-Za-z])', r'. \1', text)

    # Add space after semicolons if followed by letter
    text = re.sub(r';([A-Za-z])', r'; \1', text)

    # Add space after commas if followed by letter
    text = re.sub(r',([A-Za-z])', r', \1', text)

    # Fix multiple spaces
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def repair_text(text):
    """Apply all repairs to text."""
    if not text:
        return text

    text = fix_merged_words(text)
    text = fix_fractions(text)
    text = fix_punctuation_spacing(text)

    return text


def repair_recipe(recipe):
    """Repair a single recipe."""
    modified = False

    # Repair ingredients
    for ing in recipe.get('ingredients', []):
        if 'item' in ing:
            new_item = repair_text(ing['item'])
            if new_item != ing['item']:
                ing['item'] = new_item
                modified = True

        if 'quantity' in ing and isinstance(ing['quantity'], str):
            new_qty = fix_fractions(ing['quantity'])
            if new_qty != ing['quantity']:
                ing['quantity'] = new_qty
                modified = True

        if 'prep_note' in ing:
            new_prep = repair_text(ing['prep_note'])
            if new_prep != ing['prep_note']:
                ing['prep_note'] = new_prep
                modified = True

    # Repair instructions
    for inst in recipe.get('instructions', []):
        if isinstance(inst, dict) and 'text' in inst:
            new_text = repair_text(inst['text'])
            if new_text != inst['text']:
                inst['text'] = new_text
                modified = True

    # Repair title
    if 'title' in recipe:
        new_title = repair_text(recipe['title'])
        # Also fix title-specific issues
        new_title = re.sub(r'([a-z])([A-Z])', r'\1 \2', new_title)  # camelCase
        if new_title != recipe['title']:
            recipe['title'] = new_title
            modified = True

    # Repair notes
    for i, note in enumerate(recipe.get('notes', [])):
        if isinstance(note, str):
            new_note = repair_text(note)
            if new_note != note:
                recipe['notes'][i] = new_note
                modified = True

    return modified


def repair_recipes(recipes_file, recipe_ids=None):
    """Repair OCR-corrupted recipes."""
    with open(recipes_file) as f:
        data = json.load(f)

    repaired_count = 0
    repaired_ids = []

    for recipe in data['recipes']:
        # If specific IDs given, only repair those
        if recipe_ids and recipe['id'] not in recipe_ids:
            continue

        # Only repair flagged recipes
        if not recipe.get('needs_ocr_review'):
            continue

        if repair_recipe(recipe):
            repaired_count += 1
            repaired_ids.append(recipe['id'])

            # Mark as repaired (but still needs human verification)
            recipe['ocr_repaired'] = True
            recipe['review_reason'] = recipe.get('review_reason', '') + '; Auto-repaired, needs verification'

    # Save
    with open(recipes_file, 'w') as f:
        json.dump(data, f, indent=2)

    return repaired_count, repaired_ids


if __name__ == '__main__':
    import sys

    recipes_file = Path('data/recipes_master.json')

    print("Repairing OCR-corrupted recipes...")
    count, ids = repair_recipes(recipes_file)

    print(f"Repaired {count} recipes")
    if ids:
        print("Sample repaired IDs:")
        for rid in ids[:10]:
            print(f"  - {rid}")
