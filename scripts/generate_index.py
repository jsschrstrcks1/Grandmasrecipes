#!/usr/bin/env python3
"""
Generate lightweight recipe index for faster initial page load.

Creates recipes_index.json with only fields needed for list/search views.
Full recipe details are loaded on-demand from recipes_master.json.
"""

import json
import os

# Fields to include in the lightweight index
INDEX_FIELDS = [
    'id',
    'collection',
    'collection_display',
    'title',
    'category',
    'description',
    'servings_yield',
    'prep_time',
    'cook_time',
    'total_time',
    'ingredients',  # Needed for ingredient search
    'tags',
    'image_refs',
    'nutrition',  # Needed for nutrition filtering
]

def generate_index():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', 'data')

    master_path = os.path.join(data_dir, 'recipes_master.json')
    index_path = os.path.join(data_dir, 'recipes_index.json')

    print(f"Reading {master_path}...")
    with open(master_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    recipes = data.get('recipes', data)
    print(f"Processing {len(recipes)} recipes...")

    # Create lightweight index
    index_recipes = []
    for recipe in recipes:
        index_recipe = {k: recipe.get(k) for k in INDEX_FIELDS if k in recipe}

        # For ingredients, only keep the text for search (not full structure if complex)
        if 'ingredients' in index_recipe and index_recipe['ingredients']:
            # Keep ingredients as-is since they're needed for search
            pass

        index_recipes.append(index_recipe)

    index_data = {'recipes': index_recipes}

    # Write minified (no extra whitespace)
    print(f"Writing {index_path}...")
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, separators=(',', ':'))

    # Calculate size reduction
    master_size = os.path.getsize(master_path)
    index_size = os.path.getsize(index_path)
    reduction = (1 - index_size / master_size) * 100

    print(f"\nResults:")
    print(f"  Master: {master_size:,} bytes ({master_size/1024/1024:.1f} MB)")
    print(f"  Index:  {index_size:,} bytes ({index_size/1024/1024:.1f} MB)")
    print(f"  Reduction: {reduction:.1f}%")

    return index_path

if __name__ == '__main__':
    generate_index()
