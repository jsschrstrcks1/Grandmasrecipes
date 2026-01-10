#!/usr/bin/env python3
"""
Build Pagefind search index for recipes.

1. Fetches recipes from local and remote collections
2. Generates temporary HTML pages for each recipe (for Pagefind to index)
3. Runs Pagefind to build the search index
4. Cleans up temporary files

The resulting _pagefind/ directory contains the search index.
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.request
import urllib.error

# Remote collections to fetch (in addition to local recipes)
REMOTE_COLLECTIONS = [
    {
        "id": "mommom-baker",
        "name": "MomMom Baker",
        "base_url": "https://jsschrstrcks1.github.io/MomsRecipes",
        "urls": [
            "https://jsschrstrcks1.github.io/MomsRecipes/data/recipes.json",
        ]
    },
    {
        "id": "granny-hudson",
        "name": "Granny Hudson",
        "base_url": "https://jsschrstrcks1.github.io/Grannysrecipes",
        "urls": [
            "https://jsschrstrcks1.github.io/Grannysrecipes/data/recipes.json",
            "https://jsschrstrcks1.github.io/Grannysrecipes/granny/recipes_master.json",
            "https://raw.githubusercontent.com/jsschrstrcks1/Grannysrecipes/main/granny/recipes_master.json",
        ]
    },
    {
        "id": "all",
        "name": "Other Recipes",
        "base_url": "https://jsschrstrcks1.github.io/Allrecipes",
        "urls": [
            "https://jsschrstrcks1.github.io/Allrecipes/data/recipes.json",
            "https://jsschrstrcks1.github.io/Allrecipes/all/recipes_master.json",
            "https://raw.githubusercontent.com/jsschrstrcks1/Allrecipes/main/all/recipes_master.json",
        ]
    },
]

def fetch_remote_recipes(collection):
    """Fetch recipes from a remote collection."""
    for url in collection["urls"]:
        try:
            print(f"  Trying {url}...")
            req = urllib.request.Request(url, headers={'User-Agent': 'GrandmasKitchen/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                recipes = data.get('recipes', data if isinstance(data, list) else [])
                print(f"  Found {len(recipes)} recipes from {collection['name']}")
                return recipes
        except (urllib.error.URLError, json.JSONDecodeError, Exception) as e:
            print(f"  Failed: {e}")
            continue
    return []

def escape_html(text):
    """Escape HTML special characters."""
    if not text:
        return ''
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))

def generate_recipe_html(recipe, base_url=None):
    """Generate indexable HTML for a single recipe.

    Args:
        recipe: Recipe dict
        base_url: Base URL for remote collections (None for local)
    """
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

    # URL: local recipes use relative path, remote use absolute URL
    if base_url:
        recipe_url = f"{base_url}/recipe.html#{recipe_id}"
    else:
        recipe_url = f"recipe.html#{recipe_id}"

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
    <a data-pagefind-meta="url" href="{recipe_url}"></a>
  </article>
</body>
</html>'''

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.join(script_dir, '..')
    data_dir = os.path.join(root_dir, 'data')
    build_dir = os.path.join(root_dir, '.pagefind-build')

    # Create build directory
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)

    total_recipes = 0

    # Load local recipes (Grandma Baker)
    recipes_path = os.path.join(data_dir, 'recipes_master.json')
    print(f"Loading local recipes from {recipes_path}...")

    with open(recipes_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    local_recipes = data.get('recipes', data)
    print(f"  Found {len(local_recipes)} local recipes (Grandma Baker)")

    # Generate HTML for local recipes
    for recipe in local_recipes:
        recipe_id = recipe.get('id', 'unknown')
        html = generate_recipe_html(recipe, base_url=None)
        html_path = os.path.join(build_dir, f'local_{recipe_id}.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
    total_recipes += len(local_recipes)

    # Fetch and generate HTML for remote collections
    print("\nFetching remote collections...")
    for collection in REMOTE_COLLECTIONS:
        print(f"\n{collection['name']}:")
        remote_recipes = fetch_remote_recipes(collection)

        for recipe in remote_recipes:
            recipe_id = recipe.get('id', 'unknown')
            # Ensure collection metadata is set
            if not recipe.get('collection'):
                recipe['collection'] = collection['id']
            if not recipe.get('collection_display'):
                recipe['collection_display'] = collection['name']

            html = generate_recipe_html(recipe, base_url=collection['base_url'])
            # Prefix with collection id to avoid ID collisions
            html_path = os.path.join(build_dir, f"{collection['id']}_{recipe_id}.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)

        total_recipes += len(remote_recipes)

    print(f"\nGenerated {total_recipes} HTML files in {build_dir}")

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
