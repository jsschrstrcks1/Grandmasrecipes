#!/usr/bin/env python3
"""
Build Ingredient Index for Grandma's Kitchen Recipe Archive

Generates data/ingredient-index.json from recipes_master.json.
This pre-compiled index enables fast ingredient-based recipe search.

Features:
- Normalized ingredient names (lowercase, trimmed)
- Plural/singular normalization
- Synonym support (hamburger = ground beef)
- Recipe ID references for each ingredient
- Ingredient frequency counts

Usage:
    python scripts/build-ingredient-index.py

Output:
    data/ingredient-index.json (~50KB estimated)
"""

import json
import re
import os
from collections import defaultdict
from pathlib import Path

# Common ingredient synonyms (bidirectional)
SYNONYMS = {
    # Meats
    "hamburger": "ground beef",
    "ground beef": "hamburger",
    "hamburger meat": "ground beef",
    "beef mince": "ground beef",
    "mince": "ground beef",
    "bacon bits": "bacon",
    "pork sausage": "sausage",
    "italian sausage": "sausage",
    "breakfast sausage": "sausage",
    "chicken breast": "chicken",
    "chicken thigh": "chicken",
    "chicken thighs": "chicken",
    "chicken breasts": "chicken",

    # Dairy
    "butter": "butter",
    "margarine": "butter",
    "oleo": "butter",
    "butter or margarine": "butter",
    "margarine or butter": "butter",
    "butter or oleo": "butter",
    "oleo or butter": "butter",
    "melted butter or margarine": "butter",
    "melted margarine or butter": "butter",
    "softened butter or margarine": "butter",
    "heavy cream": "cream",
    "whipping cream": "cream",
    "heavy whipping cream": "cream",
    "half and half": "cream",
    "half & half": "cream",
    "sour cream": "sour cream",
    "cream cheese": "cream cheese",
    "cheddar": "cheddar cheese",
    "cheddar cheese": "cheddar",
    "american cheese": "cheese",
    "velveeta": "cheese",
    "parmesan": "parmesan cheese",
    "parmesan cheese": "parmesan",
    "parmigiano": "parmesan cheese",
    "mozzarella": "mozzarella cheese",
    "mozzarella cheese": "mozzarella",

    # Eggs
    "egg": "eggs",
    "eggs": "egg",
    "egg yolk": "egg yolks",
    "egg yolks": "egg yolk",
    "egg white": "egg whites",
    "egg whites": "egg white",

    # Flours and starches
    "all-purpose flour": "flour",
    "all purpose flour": "flour",
    "ap flour": "flour",
    "plain flour": "flour",
    "self-rising flour": "self rising flour",
    "self rising flour": "self-rising flour",
    "bread flour": "flour",
    "cake flour": "flour",
    "cornstarch": "corn starch",
    "corn starch": "cornstarch",

    # Sugars
    "granulated sugar": "sugar",
    "white sugar": "sugar",
    "powdered sugar": "confectioners sugar",
    "confectioners sugar": "powdered sugar",
    "icing sugar": "powdered sugar",
    "confectioner's sugar": "powdered sugar",
    "light brown sugar": "brown sugar",
    "dark brown sugar": "brown sugar",
    "packed brown sugar": "brown sugar",
    "firmly packed brown sugar": "brown sugar",

    # Oils
    "vegetable oil": "oil",
    "canola oil": "oil",
    "cooking oil": "oil",
    "olive oil": "oil",
    "evoo": "olive oil",
    "extra virgin olive oil": "olive oil",

    # Baking
    "baking soda": "baking soda",
    "bicarbonate of soda": "baking soda",
    "bicarb": "baking soda",
    "baking powder": "baking powder",

    # Tomatoes
    "tomato": "tomatoes",
    "tomatoes": "tomato",
    "cherry tomatoes": "tomatoes",
    "grape tomatoes": "tomatoes",
    "roma tomatoes": "tomatoes",
    "plum tomatoes": "tomatoes",
    "canned tomatoes": "tomatoes",
    "diced tomatoes": "tomatoes",
    "crushed tomatoes": "tomatoes",
    "tomato sauce": "tomato sauce",
    "tomato paste": "tomato paste",

    # Onions
    "onion": "onions",
    "onions": "onion",
    "yellow onion": "onions",
    "white onion": "onions",
    "red onion": "onions",
    "sweet onion": "onions",
    "vidalia onion": "onions",
    "green onion": "green onions",
    "green onions": "green onion",
    "scallion": "green onions",
    "scallions": "green onions",
    "spring onion": "green onions",
    "spring onions": "green onions",

    # Garlic
    "garlic clove": "garlic",
    "garlic cloves": "garlic",
    "minced garlic": "garlic",
    "garlic powder": "garlic powder",

    # Peppers
    "bell pepper": "bell peppers",
    "bell peppers": "bell pepper",
    "green pepper": "bell peppers",
    "red pepper": "bell peppers",
    "sweet pepper": "bell peppers",

    # Beans
    "kidney beans": "beans",
    "black beans": "beans",
    "pinto beans": "beans",
    "navy beans": "beans",
    "white beans": "beans",
    "cannellini beans": "beans",
    "great northern beans": "beans",

    # Broths/Stocks
    "chicken stock": "chicken broth",
    "chicken broth": "chicken stock",
    "beef stock": "beef broth",
    "beef broth": "beef stock",
    "vegetable stock": "vegetable broth",
    "vegetable broth": "vegetable stock",

    # Milk
    "whole milk": "milk",
    "2% milk": "milk",
    "skim milk": "milk",
    "low-fat milk": "milk",
    "evaporated milk": "evaporated milk",
    "condensed milk": "sweetened condensed milk",
    "sweetened condensed milk": "condensed milk",

    # Misc
    "vanilla": "vanilla extract",
    "vanilla extract": "vanilla",
    "pure vanilla": "vanilla extract",
    "lemon juice": "lemon juice",
    "fresh lemon juice": "lemon juice",
    "lime juice": "lime juice",
    "fresh lime juice": "lime juice",
    "worcestershire": "worcestershire sauce",
    "worcestershire sauce": "worcestershire",
    "soy sauce": "soy sauce",
    "shoyu": "soy sauce",
}

# Words to strip from ingredients for normalization
STRIP_WORDS = [
    "fresh", "dried", "frozen", "canned", "chopped", "diced", "sliced",
    "minced", "crushed", "ground", "grated", "shredded", "melted",
    "softened", "room temperature", "cold", "warm", "hot", "cooked",
    "uncooked", "raw", "prepared", "peeled", "seeded", "pitted",
    "boneless", "skinless", "bone-in", "skin-on", "trimmed",
    "large", "medium", "small", "extra-large", "jumbo", "mini",
    "thick", "thin", "finely", "coarsely", "roughly",
    "optional", "or more", "to taste", "as needed", "for garnish",
]

# Plural patterns for normalization
PLURAL_RULES = [
    (r"ies$", "y"),      # berries -> berry
    (r"oes$", "o"),      # tomatoes -> tomato, potatoes -> potato
    (r"ves$", "f"),      # loaves -> loaf
    (r"ves$", "fe"),     # knives -> knife
    (r"s$", ""),         # general plural
]


def normalize_ingredient(name):
    """
    Normalize an ingredient name for consistent matching.

    - Lowercase
    - Strip common modifiers (fresh, chopped, etc.)
    - Handle plurals
    - Trim whitespace
    """
    if not name:
        return ""

    # Lowercase and trim
    normalized = name.lower().strip()

    # Remove content in parentheses
    normalized = re.sub(r'\([^)]*\)', '', normalized)

    # Strip common modifiers
    for word in STRIP_WORDS:
        # Word boundary matching to avoid partial matches
        pattern = r'\b' + re.escape(word) + r'\b'
        normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)

    # Clean up extra whitespace
    normalized = ' '.join(normalized.split())

    # Remove leading/trailing punctuation
    normalized = normalized.strip('.,;:')

    return normalized.strip()


def singularize(word):
    """
    Convert plural to singular form.
    Simple rule-based approach for common cooking ingredients.
    """
    word = word.lower().strip()

    # Special cases that don't follow rules
    irregulars = {
        "leaves": "leaf",
        "halves": "half",
        "dice": "dice",
        "mice": "mouse",
        "teeth": "tooth",
        "feet": "foot",
        "geese": "goose",
        "men": "man",
        "women": "woman",
        "children": "child",
        "fish": "fish",
        "sheep": "sheep",
        "deer": "deer",
        "series": "series",
        "species": "species",
    }

    if word in irregulars:
        return irregulars[word]

    # Apply plural rules
    for pattern, replacement in PLURAL_RULES:
        if re.search(pattern, word):
            singular = re.sub(pattern, replacement, word)
            # Avoid over-singularizing (e.g., "cheese" shouldn't become "chees")
            if len(singular) >= 2:
                return singular

    return word


def get_canonical_name(ingredient):
    """
    Get the canonical (primary) name for an ingredient.
    Uses synonym mapping to normalize variants.
    """
    normalized = normalize_ingredient(ingredient)

    # Check direct synonym match
    if normalized in SYNONYMS:
        return SYNONYMS[normalized]

    # Try singularized form
    singular = singularize(normalized)
    if singular in SYNONYMS:
        return SYNONYMS[singular]

    return normalized


def extract_base_ingredient(item):
    """
    Extract the base ingredient name from an ingredient line.
    Handles compound ingredients like "cheddar cheese, shredded"
    """
    # Split on common separators
    base = item.split(',')[0]
    base = base.split(' or ')[0]
    base = base.split('/')[0]

    return normalize_ingredient(base)


def build_ingredient_index(recipes):
    """
    Build the ingredient index from a list of recipes.

    Returns a dictionary with:
    - ingredients: dict mapping canonical names to recipe IDs
    - synonyms: dict mapping variant names to canonical names
    - frequency: dict mapping canonical names to usage counts
    - all_names: list of all ingredient names for autocomplete
    """
    # Maps canonical ingredient name -> set of recipe IDs
    ingredient_recipes = defaultdict(set)

    # Maps all seen names to their canonical form
    name_to_canonical = {}

    # Frequency count for each canonical ingredient
    frequency = defaultdict(int)

    # All unique ingredient names seen (for autocomplete)
    all_names = set()

    for recipe in recipes:
        recipe_id = recipe.get('id', '')
        ingredients = recipe.get('ingredients', [])

        for ing in ingredients:
            if not isinstance(ing, dict):
                continue

            item = ing.get('item', '')
            if not item:
                continue

            # Store original name
            all_names.add(item.lower().strip())

            # Get normalized and canonical names
            normalized = normalize_ingredient(item)
            canonical = get_canonical_name(item)
            base = extract_base_ingredient(item)

            # Map names to canonical
            name_to_canonical[item.lower().strip()] = canonical
            name_to_canonical[normalized] = canonical
            if base:
                name_to_canonical[base] = canonical

            # Add recipe to ingredient's recipe list
            ingredient_recipes[canonical].add(recipe_id)
            frequency[canonical] += 1

            # Also index the base ingredient separately if different
            if base and base != canonical:
                base_canonical = get_canonical_name(base)
                ingredient_recipes[base_canonical].add(recipe_id)

    # Convert sets to sorted lists for JSON serialization
    ingredients_dict = {
        name: sorted(list(recipe_ids))
        for name, recipe_ids in ingredient_recipes.items()
    }

    # Sort all_names list and frequency dict
    sorted_names = sorted(all_names)
    sorted_frequency = dict(sorted(
        frequency.items(),
        key=lambda x: (-x[1], x[0])  # Sort by frequency desc, then name asc
    ))

    return {
        "meta": {
            "version": "1.0.0",
            "description": "Pre-compiled ingredient search index for Grandma's Kitchen",
            "total_ingredients": len(ingredients_dict),
            "total_recipes_indexed": len(recipes),
        },
        "ingredients": ingredients_dict,
        "synonyms": SYNONYMS,
        "name_mapping": name_to_canonical,
        "frequency": sorted_frequency,
        "all_names": sorted_names,
    }


def main():
    """Main entry point."""
    # Get paths relative to script location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    recipes_path = project_root / "data" / "recipes_master.json"
    output_path = project_root / "data" / "ingredient-index.json"

    print(f"Building ingredient index...")
    print(f"  Source: {recipes_path}")
    print(f"  Output: {output_path}")

    # Load recipes
    if not recipes_path.exists():
        print(f"Error: {recipes_path} not found")
        return 1

    with open(recipes_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    recipes = data.get('recipes', [])
    print(f"  Found {len(recipes)} recipes")

    # Build index
    index = build_ingredient_index(recipes)

    print(f"  Indexed {index['meta']['total_ingredients']} unique ingredients")

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    # Report file size
    size_kb = output_path.stat().st_size / 1024
    print(f"  Output size: {size_kb:.1f} KB")

    # Show top 10 most common ingredients
    print("\n  Top 10 most common ingredients:")
    for i, (name, count) in enumerate(list(index['frequency'].items())[:10], 1):
        recipe_count = len(index['ingredients'].get(name, []))
        print(f"    {i}. {name}: {count} uses in {recipe_count} recipes")

    print("\nDone!")
    return 0


if __name__ == "__main__":
    exit(main())
