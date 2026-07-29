# Repository Status Review

**Reviewer:** Claude (Opus 4.5)
**Date:** 2026-02-05
**Branch:** claude/review-repo-status-6VORt
**Scope:** Full repository health check — structure, data, code, documentation, and maintenance

---

## Executive Summary

The Grandma's Kitchen Family Recipe Archive is a **mature, well-structured project** that has grown from 5 recipes to **9,396 recipes** across 4 family collections. The codebase is production-ready with comprehensive tooling, validation, and AI-assisted workflows. However, several maintenance items need attention: missing local image processing pipeline, outdated README, health feature bugs documented but not yet fixed, and a minor recipe count discrepancy.

**Overall Health: GOOD — with targeted maintenance needed**

---

## Repository Metrics

| Metric | Value |
|--------|-------|
| Total recipes | 9,396 |
| Grandma Baker (local) | 938 |
| MomMom Baker (remote) | 2,553 |
| Granny Hudson (remote) | 184 |
| Other Family (remote) | 5,722 |
| Total images | 1,996 |
| Local images (data/) | 722 |
| Remote images (data/all/) | 1,274 |
| Python scripts | 20 |
| JavaScript modules | 7 |
| CSS lines | 7,339 |
| JS lines (main) | 5,351 |

---

## Status by Area

### 1. Data Integrity — HEALTHY (minor issue)

**recipes_master.json** (28MB, 1,058,690 lines):
- Hub format with metadata + recipe array
- Metadata claims 9,397 total recipes; actual array contains 9,396 (off by 1)
- All 4 collections present and properly structured
- `[UNCLEAR]` markers correctly used for uncertain transcriptions

**Validation results** (`python scripts/validate-recipes.py`):
- **0 errors**
- **10 warnings:**
  - 5 suspicious ingredient quantities (e.g., 5 tsp baking soda, 8 cups sugar)
  - 5 recipes missing nutrition data

**Action items:**
- [ ] Investigate recipe count discrepancy (metadata 9,397 vs actual 9,396)
- [ ] Review 5 flagged suspicious quantities for accuracy

### 2. Image Management — NEEDS ATTENTION

**Image inventory:**
- 722 Grandma Baker images stored flat in `data/` (correct per CLAUDE.md)
- Naming convention consistent: `Grandmas-recipes - N.jpeg`
- No prohibited subdirectories (compliant)

**Processing status:**
- 924 images flagged as oversized (exceed 2000px API limit)
- **`data/processed/` directory for local images does NOT exist**
- Remote collection (`data/all/processed/`) has processed versions
- Image safeguards last updated: 2026-01-25
- 0 broken images detected

**Action items:**
- [ ] **HIGH PRIORITY:** Run `python scripts/process_images.py` to create `data/processed/` with AI-safe versions
- [ ] Verify all 722 local images have processed counterparts after running

### 3. Web Frontend — HEALTHY (feature-rich)

**Core files:**
- `index.html` (875 lines) — Hub page with search, filters, collection switching
- `recipe.html` (139 lines) — Recipe detail template
- `script.js` (5,351 lines) — Main application logic
- `styles.css` (7,339 lines) — 1950s retro kitchen theme

**Advanced features implemented:**
- Recipe Scaling Intelligence (`scaling-intelligence.js`, 665 lines)
- Diabetic-Friendly Recipe Converter (`diabetic-converter.js`, 18K)
- Heart-Smart Recipe Converter (`heart-smart-converter.js`, 23K)
- Milk Substitution Tool (`milk-substitution.js`, 55K)
- Protein & Vegetable Substitution (`protein-substitution.js`)
- Pagefind search integration (`_pagefind/` directory)
- Cross-repository aggregation from 4 family collections

**Minified assets available:** `script.min.js`, `styles.min.css`

### 4. Health Features — HAS KNOWN ISSUES

Per the audit report (`.claude/HEALTH_AUDIT_REPORT.md`, dated 2026-01-30):

**21 issues documented but not yet fixed:**

| Severity | Count | Examples |
|----------|-------|---------|
| Critical | 3 | ACE inhibitor/potassium interaction under-classified; detection logic first-match-only bug; reverse partial match false positives |
| High | 9 | False allergen flags (cream of tartar as dairy, coconut milk as dairy, water chestnuts as tree nuts, peanut butter as dairy) |
| Medium | 5 | Various inaccuracies and outdated information |
| Low | 4 | Code quality issues |

**Action items:**
- [ ] **CRITICAL:** Upgrade ACE inhibitor/potassium severity from "moderate" to "high"
- [ ] **CRITICAL:** Fix first-match-only bug in `script.js:871-876` — collect all matches, merge, deduplicate
- [ ] **CRITICAL:** Fix reverse partial match in `script.js:872` — remove or guard `flaggedIng.includes(ingText)`
- [ ] Fix false allergen classifications for cream of tartar, coconut milk, water chestnuts, peanut butter

### 5. Scripts & Tooling — HEALTHY

20 Python scripts covering:

| Category | Scripts |
|----------|---------|
| Validation | `validate-recipes.py` |
| Image processing | `process_images.py`, `optimize_images.py`, `image_safeguards.py` |
| Aggregation | `aggregate_collections.py`, `aggregate_tips.py` |
| Search/indexing | `build-ingredient-index.py`, `build-pagefind.py`, `generate_index.py` |
| Duplicate detection | `analyze_duplicates.py`, `check-duplicates.py` |
| Data repair | `repair_ocr.py`, `convert_string_to_object.py` |
| Nutrition | `estimate_nutrition.py`, `estimate_nutrition_elite.py` |
| Utilities | `parse_yield.py`, `shard_recipes.py`, `execute_merges.py`, `minify.py` |

All scripts present and functional. Validation runs cleanly with 0 errors.

### 6. .claude/ Infrastructure — EXCELLENT

**Configuration:**
- `settings.json` — Hooks for post-write validation and pre-read image safety
- `skill-rules.json` — Auto-activation for transcription/validation/image-safety

**Documentation (9 files):**
- `ONBOARDING.md` — New session guidance
- `MAINTENANCE.md` (29K) — Detailed workflows
- `PENDING_TASKS.md` (68K) — Feature tracking with completion status
- `HEALTH_AUDIT_REPORT.md` (17K) — Health features review
- `DUPLICATE_CHECK_REPORT.md` — Cross-repo duplicate analysis
- `CROSS_REPO_STANDARDS.md` — Sync standards
- `VARIANT_REVIEW_PLAN.md` — Recipe variant management
- `ADULTERANT-COMPANION-GUIDE.md`, `CHEESE-RECIPE-GUIDELINES.md`

**Hooks (2):**
- `post-write-validate.sh` — Auto-validates after edits
- `image-safety-check.sh` — Warns before reading oversized images

**Skills (2):**
- `recipe-transcription/SKILL.md` — OCR and handwritten text guidelines
- `recipe-validation/SKILL.md` — Schema validation rules

### 7. Documentation — MIXED

**CLAUDE.md (v1.4):** Comprehensive, current, well-structured. Serves as the authoritative project guide.

**README.md:** **Significantly outdated.** Key issues:
- States "5 unique recipes extracted from 6 scanned images" (actual: 938 local, 9,396 total)
- References `site/` subdirectory structure (actual: files are at root)
- References `processed_images.json` (doesn't exist in current structure)
- Recipe table shows only 5 original recipes
- Missing mention of hub aggregation, health features, scaling tools

**Action items:**
- [ ] Update README.md to reflect current state (938 local recipes, 9,396 total, root-level web files, hub architecture)

### 8. Hub/Aggregation — HEALTHY

**collections.json** properly configured with:
- 1 local collection (grandma-baker)
- 3 remote collections with sharding (mommom-baker, granny-hudson, all)
- GitHub Pages URLs correctly pointed

### 9. Git Status — CLEAN

- Branch: `claude/review-repo-status-6VORt`
- Working tree: clean
- Recent commits show active, well-organized development
- Major recent themes: health features audit, image consolidation, recipe scaling, protein substitution tool

---

## Priority Action Items

### Critical (should fix soon)
1. **Run image processing pipeline** — 924 oversized images have no processed versions
2. **Fix health feature detection bugs** — 3 critical issues in `script.js` allergen/drug interaction detection
3. **Upgrade ACE inhibitor severity** — Potentially life-threatening interaction under-classified

### High (should fix)
4. **Fix false allergen classifications** — 9 incorrect ingredient flags erode user trust
5. **Update README.md** — Severely outdated, misleading for new visitors

### Medium (good to fix)
6. **Resolve recipe count discrepancy** — Metadata says 9,397, array has 9,396
7. **Review suspicious quantities** — 5 recipes flagged with unusual measurements
8. **Address remaining health audit issues** — 5 medium + 4 low severity items

---

## What's Working Well

1. **Excellent process discipline** — Hooks, validation scripts, and safety checks enforce quality
2. **Comprehensive feature set** — Health converters, scaling intelligence, substitution tools, search
3. **Clean data structure** — Flat image paths, proper collection IDs, consistent schema
4. **Cross-repository architecture** — Hub aggregates 4 family collections seamlessly
5. **Thorough documentation** — CLAUDE.md is a model project guide; .claude/ has detailed session continuity docs
6. **Validation passes cleanly** — 0 errors across 9,396 recipes
7. **Consistent [UNCLEAR] usage** — Fidelity-first approach properly followed
8. **Active maintenance** — Regular commits with clear messages showing ongoing care

---

*"She looketh well to the ways of her household, and eateth not the bread of idleness."*
— Proverbs 31:27
