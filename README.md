# Grandma's Recipe Archive

A treasured collection of family recipes from Grandma Baker, plus the
toolkit that converts everyday recipes into diabetic, heart-smart, and
substitution-aware variants. Preserved with love and offered freely.

> *Soli Deo Gloria.*

---

## Table of Contents

- [About this project](#about-this-project)
- [Family Recipe Archive (multi-repo)](#family-recipe-archive-multi-repo)
- [What's in this repo](#whats-in-this-repo)
- [Smart converters](#smart-converters)
- [Project structure](#project-structure)
- [Quick start](#quick-start)
- [Generate the e-book / PDF](#generate-the-e-book--pdf)
- [Adding new recipes](#adding-new-recipes)
- [Recipe JSON schema](#recipe-json-schema)
- [Current recipes](#current-recipes)
- [Known issues & flags](#known-issues--flags)
- [Validation & integrity](#validation--integrity)
- [Recommended tools for future processing](#recommended-tools-for-future-processing)
- [Multi-LLM integration](#multi-llm-integration)
- [Contributing](#contributing)
- [License](#license)

---

## About this project

This archive preserves Grandma Baker's recipes — handwritten cards,
newspaper clippings, magazine cuttings, and other family treasures.
The recipes span her journey from Michigan to Florida, representing
both Northern and Southern culinary traditions.

This repo also doubles as the **converter and calculator host** for the
recipe family of repos. Standalone JavaScript modules implement
diabetic, heart-smart, milk-substitution, protein-substitution, and
intelligent-scaling logic that can be embedded in any of the sister
recipe sites.

**Current status:** small but growing recipe set; converter/calculator
toolkit is the most active area. See [Current recipes](#current-recipes).

---

## Family Recipe Archive (multi-repo)

| Repo | Collection |
|---|---|
| [MomsRecipes](https://github.com/jsschrstrcks1/MomsRecipes) | MomMom Baker (heirloom recipes) |
| **Grandmasrecipes** | **Grandma Baker** *(this repo — also hosts converters)* |
| [Grannysrecipes](https://github.com/jsschrstrcks1/Grannysrecipes) | Granny Hudson (Florida → Boston → back) |
| [Allrecipes](https://github.com/jsschrstrcks1/Allrecipes) | Reference cookbooks & magazines |

Grandma's repo doubles as the **aggregator** in the family — its
calculators and substitutions can be linked into any of the others.

---

## What's in this repo

- A static recipe site (HTML + CSS + vanilla JS), Pagefind-indexed.
- A **PWA** (`sw.js`, `manifest.webmanifest`) with offline support.
- Five smart-conversion engines (diabetic, heart-smart, milk,
  protein, scaling) — see [Smart converters](#smart-converters).
- A standalone **calculator** page (`calculator.html`) that ties the
  engines together for ad-hoc conversions.
- A printable e-book (`ebook/book.html`) for Calibre / wkhtmltopdf /
  browser-print export.

---

## Smart converters

Five JavaScript modules ship as part of this repo and are usable on any
recipe page:

| Module | What it does |
|---|---|
| [`diabetic-converter.js`](diabetic-converter.js) | Substitutes high-glycemic ingredients, recalculates carbs and added sugar, flags when a recipe can't be converted safely. |
| [`heart-smart-converter.js`](heart-smart-converter.js) | Reduces sodium and saturated fat, swaps cooking oils, preserves the cooking technique. |
| [`milk-substitution.js`](milk-substitution.js) | Maps dairy milks to plant-based alternatives (almond, oat, soy, coconut) accounting for fat content and sweetness. |
| [`protein-substitution.js`](protein-substitution.js) | Swaps proteins (beef ↔ pork ↔ poultry ↔ plant) with cook-time corrections. |
| [`scaling-intelligence.js`](scaling-intelligence.js) | Scales recipes by serving count, **not** by linear multiplication — it knows that doubling salt isn't doubling the dish. |

The converters are deliberately conservative: when a substitution would
fundamentally change the recipe (e.g. butter in a laminated dough), they
refuse and explain why.

See [`PLAN-nutrition-facts.md`](PLAN-nutrition-facts.md) for the planned
nutrition-facts panel that ties all five converters together.

---

## Project structure

```
Grandmasrecipes/
├── CLAUDE.md                      # AI assistant context
├── PLAN-nutrition-facts.md        # Nutrition-facts integration plan
├── README.md                      # This file
├── data/
│   ├── *.jpeg                     # Original scanned recipe images
│   ├── recipes_master.json        # All recipes
│   └── processed_images.json      # Scan processing log
├── _pagefind/                     # Pagefind search index
├── docs/                          # Project docs (architecture, decisions)
├── ebook/
│   ├── book.html                  # Print-optimized e-book
│   └── print.css                  # Print stylesheet
├── scripts/                       # Build / validation utilities
├── index.html                     # Home page (search + filters)
├── recipe.html                    # Recipe detail page
├── calculator.html                # Standalone converter UI
├── diabetic-converter.js
├── heart-smart-converter.js
├── milk-substitution.js
├── protein-substitution.js
├── scaling-intelligence.js
├── script.js / script.min.js      # Site bundle
├── styles.css / styles.min.css    # Stylesheet (+ minified)
├── sw.js                          # Service Worker (PWA)
├── robots.txt
└── license                        # GNU AGPL v3
```

---

## Quick start

### View the site locally

```bash
# Python (recommended)
cd Grandmasrecipes
python -m http.server 8000

# or Node.js
npx serve .

# or PHP
php -S localhost:8000
```

Open <http://localhost:8000>. The Service Worker activates after the
first load; subsequent loads are offline-capable.

### Host on GitHub Pages / Netlify / Vercel

Pure static — no build required. Point the publish directory at the
repo root (or the `/site/` subfolder if you keep the legacy layout).

---

## Generate the e-book / PDF

#### Browser print (easiest)

1. Open `ebook/book.html` in a browser.
2. `Ctrl+P` (or `Cmd+P`) → "Save as PDF".
3. Set margins to "None" or "Minimum"; enable "Background graphics".

#### `wkhtmltopdf`

```bash
wkhtmltopdf \
  --enable-local-file-access \
  --page-size Letter \
  --margin-top 0.75in --margin-bottom 0.75in \
  --margin-left 1in --margin-right 1in \
  ebook/book.html grandmas-recipes.pdf
```

#### Pandoc

```bash
pandoc ebook/book.html \
  -o grandmas-recipes.pdf \
  --pdf-engine=wkhtmltopdf \
  --css=ebook/print.css
```

#### Calibre (EPUB / MOBI)

Add `ebook/book.html` to Calibre, "Convert book", choose your output
format.

---

## Adding new recipes

1. **Scan** at 300 DPI or higher; save as JPEG in `data/` as
   `Grandmas-recipes - N.jpeg`.
2. **Extract** following [`CLAUDE.md`](CLAUDE.md):
   - Analyze the scan for orientation and content.
   - Extract recipe data per the JSON schema.
   - Check for duplicates against existing recipes.
   - Append to `data/recipes_master.json`.
   - Update `data/processed_images.json`.
3. **Update the e-book** (`ebook/book.html`):
   - Add to Table of Contents.
   - Insert recipe in the appropriate section.
   - Update the Index.
4. **Validate** (see below) and commit.

The `recipe-transcription` and `recipe-validation` skills automate
steps 2 and 4 when working with Claude Code.

---

## Recipe JSON schema

```json
{
  "id": "recipe-slug",
  "title": "Recipe Title",
  "attribution": "Source/Author",
  "source_note": "Where it came from",
  "description": "Brief description",
  "category": "desserts|mains|sides|etc",
  "servings_yield": "4 servings",
  "prep_time": "15 minutes",
  "cook_time": "30 minutes",
  "total_time": "45 minutes",
  "ingredients": [
    {"item": "flour", "quantity": "2", "unit": "cups", "prep_note": "sifted"}
  ],
  "instructions": [
    {"step": 1, "text": "Preheat oven to 350°F."}
  ],
  "temperature": "350°F (175°C)",
  "pan_size": "9x13 inch pan",
  "notes": ["Any additional notes"],
  "tags": ["dessert", "holiday", "vintage"],
  "confidence": {"overall": "high|medium|low", "flags": []},
  "image_refs": ["filename.jpeg"]
}
```

---

## Current recipes

| Recipe | Category | Source | Confidence |
|---|---|---|---|
| Ginger-Onion Lo Mein | Mains | Magazine clipping | Medium\* |
| Glazed Carrots | Sides | Tampa Tribune, 1994 | High |
| Jubilie Jumbles | Desserts | Typed card (Betty Crocker, 1955) | High |
| Original Chex Party Mix | Snacks | Cereal box | High |
| She's a Geisha Cocktail | Beverages | Izumi restaurant menu | High |

*\*Instructions partially inferred from standard technique.*

## Known issues & flags

### Ginger-Onion Lo Mein

- Original clipping was cut off.
- Steps 5–7 inferred from standard lo-mein technique.
- **If you find the original source, please update.**

### Jubilie Jumbles

- Original card showed "2 tsp" butter in glaze.
- Corrected to "2 tbsp" per the canonical Carnation recipe.
- Spelling "Jubilie" preserved from original (may be "Jubilee").

---

## Validation & integrity

```bash
# JSON syntax
python -m json.tool data/recipes_master.json > /dev/null && echo "JSON valid"

# Required-field check
python -c "
import json
with open('data/recipes_master.json') as f:
    data = json.load(f)
    for r in data['recipes']:
        assert 'id' in r, f'Missing id in {r.get(\"title\", \"unknown\")}'
        assert 'title' in r, f'Missing title in {r[\"id\"]}'
        assert 'ingredients' in r, f'Missing ingredients in {r[\"title\"]}'
        assert 'instructions' in r, f'Missing instructions in {r[\"title\"]}'
print('All recipes valid!')
"
```

The integrity rules:

- Every recipe must trace back to a real source — handwriting, clipping,
  or family memory. **No AI-invented recipes.**
- Inferred steps are flagged via `confidence.flags`.
- Spelling of original cards is preserved verbatim.
- Substitution converters never silently change a recipe's category or
  cuisine.

---

## Recommended tools for future processing

- **OCR:** EasyOCR, PaddleOCR, Tesseract.
- **Image preprocessing:** OpenCV, unpaper, ScanTailor.
- **E-book generation:** Calibre, Pandoc, ebooklib.

---

## Multi-LLM integration

Defaults to **`recipe` mode** in the multi-LLM orchestrator hosted in
[ken](https://github.com/jsschrstrcks1/ken).

| Skill | Usage |
|---|---|
| `/consult gpt structure "..."` | Quick second opinion on extracted recipe shape |
| `/orchestrate recipe "<task>"` | Full pipeline: transcribe → validate → integrate |
| Cognitive memory | Scope `/Grandmasrecipes` |

The `milk-substitution` skill is published as a Claude Code skill that
wraps `milk-substitution.js`; see `.claude/skills/milk-substitution/`
for usage.

#### Setup (per session)

```bash
pip3 install -q -r /home/user/ken/orchestrator/requirements.txt
```

---

## Contributing

This is a family project. If you're family and have:

- Additional scans of Grandma's recipes
- Corrections to existing recipes
- Memories or context about specific recipes

Please reach out, or open a PR on a `claude/<topic>-<id>` branch.

---

## License

GNU Affero General Public License v3.0 — see [`license`](license).

The recipe text and images are a family treasure; please use respectfully.

---

*"She looketh well to the ways of her household, and eateth not the
bread of idleness." — Proverbs 31:27*


## Memorial photo album

`Memorial/Grandma/` holds the family's photo and video album for Grandma (606 photos, 12 videos), moved here from the Grannysrecipes repository on 2026-08-30 — the images belong with her collection. These are family photos, not recipe scans; recipe card scans live in `data/`.
