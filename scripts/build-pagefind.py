#!/usr/bin/env python3
"""
Build Pagefind search index for recipes.

1. Generates temporary HTML pages for each recipe (for Pagefind to index)
2. Runs Pagefind to build the search index
3. Cleans up temporary files

The resulting _pagefind/ directory contains the search index.
"""

import json
import os
import shutil
import subprocess
import sys

def escape_html(text):
    """Escape HTML special characters."""
    if not text:
        return ''
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))

def generate_recipe_html(recipe):
    """Generate indexable HTML for a single recipe."""
    recipe_id = recipe.get('id', '')
    title = escape_html(recipe.get('title', ''))
    category = escape_html(recipe.get('category', ''))
    description = escape_html(recipe.get('description', ''))
    collection = escape_html(recipe.get('collection_display', recipe.get('collection', '')))

    # Extract ingredient text
    ingredients = recipe.get('ingredients', [])
    ingredient_text = []
    for ing in ingredients:
        if isinstance(ing, dict):
            ingredient_text.append(escape_html(ing.get('item', '')))
        elif isinstance(ing, str):
            ingredient_text.append(escape_html(ing))
    ingredients_html = ' '.join(ingredient_text)

    # Tags
    tags = recipe.get('tags', [])
    tags_html = ' '.join(escape_html(t) for t in tags)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
</head>
<body>
  <article data-pagefind-body>
    <h1 data-pagefind-meta="title" data-pagefind-weight="10">{title}</h1>
    <p data-pagefind-meta="category" data-pagefind-filter="category">{category}</p>
    <p data-pagefind-meta="collection" data-pagefind-filter="collection">{collection}</p>
    <p data-pagefind-meta="description">{description}</p>
    <div data-pagefind-weight="5">{ingredients_html}</div>
    <div data-pagefind-meta="tags">{tags_html}</div>
    <a data-pagefind-meta="url" href="recipe.html#{recipe_id}"></a>
  </article>
</body>
</html>'''

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.join(script_dir, '..')
    data_dir = os.path.join(root_dir, 'data')
    build_dir = os.path.join(root_dir, '.pagefind-build')

    # Load recipes
    recipes_path = os.path.join(data_dir, 'recipes_master.json')
    print(f"Loading recipes from {recipes_path}...")

    with open(recipes_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    recipes = data.get('recipes', data)
    print(f"Found {len(recipes)} recipes")

    # Create build directory
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)

    # Generate HTML for each recipe
    print("Generating indexable HTML...")
    for recipe in recipes:
        recipe_id = recipe.get('id', 'unknown')
        html = generate_recipe_html(recipe)
        html_path = os.path.join(build_dir, f'{recipe_id}.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)

    print(f"Generated {len(recipes)} HTML files in {build_dir}")

    # Run Pagefind
    print("\nRunning Pagefind...")
    pagefind_output = os.path.join(root_dir, '_pagefind')

    try:
        result = subprocess.run(
            ['npx', '-y', 'pagefind',
             '--site', build_dir,
             '--output-path', pagefind_output],
            capture_output=True,
            text=True,
            cwd=root_dir
        )

        if result.returncode != 0:
            print(f"Pagefind error: {result.stderr}")
            sys.exit(1)

        print(result.stdout)

    except FileNotFoundError:
        print("Error: npx not found. Please install Node.js.")
        sys.exit(1)

    # Clean up build directory
    print("\nCleaning up...")
    shutil.rmtree(build_dir)

    # Show results
    if os.path.exists(pagefind_output):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(pagefind_output):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)

        print(f"\nPagefind index created: {pagefind_output}")
        print(f"Total index size: {total_size / 1024:.1f} KB")

        # List key files
        print("\nKey files:")
        for f in ['pagefind.js', 'pagefind-ui.js', 'pagefind-ui.css']:
            fp = os.path.join(pagefind_output, f)
            if os.path.exists(fp):
                size = os.path.getsize(fp)
                print(f"  {f}: {size / 1024:.1f} KB")

if __name__ == '__main__':
    main()
