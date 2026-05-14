# Grandma's Kitchen — AI Assistant Context

**Version:** 2.1 (lean hub + skills index)
**Last updated:** 2026-05-10

> **Soli Deo Gloria.** A labor of love by a Reformed Baptist family. These
> recipes — many handwritten and irreplaceable — matter deeply.
> **Accuracy beats speed.**

This repo serves two functions:

1. **Collection** — Grandma Baker's recipes (handwritten cards, Michigan → Florida).
2. **Hub** — the central site that can aggregate from all four family recipe repos.

---

## Skills

Full skill catalog (18 skills) is documented in [`SKILLS.md`](SKILLS.md) — human-facing index with activation modes, trigger keywords, and example prompts.

**Read SKILLS.md at session start.** Recipe-domain skills (`recipe-transcription`, `recipe-validation`) and the standard household kit (16 skills) are configured under `.claude/skills/`. The five smart converters ship as JavaScript modules (not skills) and run in the browser.

---

## Quick Start (read first)

1. **Images are FLAT** in `data/` — no subdirectories. Use `data/processed/` for AI reads.
2. **NEVER delete handwritten images** — irreplaceable family heirlooms.
3. **NEVER invent** ingredients, steps, or measurements. Mark unclear text `[UNCLEAR]`.
4. **API limit: 100 images / request, 2000 px / image.** Batch carefully.
5. **Run `python scripts/validate-recipes.py`** after every change.
6. **Commit and push before ending a session.** Document WIP in `.claude/*.md`.

Decision priority: **accuracy → preservation → fidelity → readability**.

---

## Essential Reading

### Skills index

| File | What it covers |
|---|---|
| [`SKILLS.md`](SKILLS.md) | **Skills index — read at session start** |

### Standards (extracted)

| File | What it covers |
|---|---|
| [`.claude/standards/OCR_STANDARDS.md`](.claude/standards/OCR_STANDARDS.md) | Character confusion, measurement standardization, dual-temperature format |
| [`.claude/standards/IMAGE_WORKFLOW.md`](.claude/standards/IMAGE_WORKFLOW.md) | Flat-path rule, 2000 px / 100-image limits, manifest commands |
| [`.claude/standards/RECIPE_SCHEMA.md`](.claude/standards/RECIPE_SCHEMA.md) | Recipe JSON schema and category list |
| [`.claude/standards/GUARDRAILS.md`](.claude/standards/GUARDRAILS.md) | Accept/reject table, do/don't list, common errors to avoid |
| [`.claude/standards/HUB_AGGREGATION.md`](.claude/standards/HUB_AGGREGATION.md) | Cross-repo aggregation, FAMILY_COLLECTIONS array |

### Operations

| File | What it covers |
|---|---|
| [`.claude/MAINTENANCE.md`](.claude/MAINTENANCE.md) | Detailed maintenance workflows |
| [`.claude/ONBOARDING.md`](.claude/ONBOARDING.md) | New-session prompt |
| [`.claude/CROSS_REPO_STANDARDS.md`](.claude/CROSS_REPO_STANDARDS.md) | Cross-repository sync standards |
| [`.claude/mcp-servers.md`](.claude/mcp-servers.md) | MCP server documentation |
| [`README.md`](README.md) | Public-facing overview |

---

## Repository Structure

```
Grandmasrecipes/
├── SKILLS.md                 # Skills index (NEW)
├── CLAUDE.md                 # This hub
├── README.md                 # Public-facing overview
├── index.html               # Hub + local recipes
├── recipe.html              # Recipe detail page
├── styles.css / script.js   # Site bundle (script.js does aggregation)
├── calculator.html          # Standalone converter UI
├── *-converter.js / milk-substitution.js / scaling-intelligence.js
├── sw.js / manifest.webmanifest # PWA
├── .claude/
│   ├── settings.json        # Hooks + permissions
│   ├── skill-rules.json     # Skill auto-activation
│   ├── MAINTENANCE.md       # Detailed maintenance workflows
│   ├── ONBOARDING.md        # New-session prompt
│   ├── CROSS_REPO_STANDARDS.md
│   ├── mcp-servers.md
│   ├── standards/           # Extracted reference files
│   ├── hooks/
│   │   ├── post-write-validate.sh
│   │   └── image-safety-check.sh
│   └── skills/              # 18 skills (see SKILLS.md)
├── data/
│   ├── *.jpeg               # FLAT — no subdirectories!
│   ├── processed/           # AI-safe ≤2000 px copies
│   ├── recipes_master.json  # Grandma Baker's recipes (LOCAL)
│   └── collections.json     # Hub configuration
├── scripts/
│   ├── validate-recipes.py
│   ├── process_images.py
│   └── image_safeguards.py
└── ebook/                   # Print generation
```

### CRITICAL: Image Path Structure

```
CORRECT:   data/Grandmas-recipes - 12.jpeg
WRONG:     data/grandma/Grandmas-recipes - 12.jpeg   (subdirectory does not exist)
```

---

## Family Repositories

| Collection | Repo | Pages site | Collection ID |
|---|---|---|---|
| Grandma Baker | [Grandmasrecipes](https://github.com/jsschrstrcks1/Grandmasrecipes) | [Live](https://jsschrstrcks1.github.io/Grandmasrecipes/) | `grandma-baker` |
| MomMom Baker | [MomsRecipes](https://github.com/jsschrstrcks1/MomsRecipes) | [Live](https://jsschrstrcks1.github.io/MomsRecipes/) | `mommom-baker` |
| Granny Hudson | [Grannysrecipes](https://github.com/jsschrstrcks1/Grannysrecipes) | [Live](https://jsschrstrcks1.github.io/Grannysrecipes/) | `granny-hudson` |
| Other Recipes | [Allrecipes](https://github.com/jsschrstrcks1/Allrecipes) | [Live](https://jsschrstrcks1.github.io/Allrecipes/) | `all` |

Aggregation logic lives in `.claude/standards/HUB_AGGREGATION.md`.

---

## Non-Negotiable Rules

1. **NEVER delete handwritten images** — ever.
2. **NEVER invent** ingredients, steps, or measurements.
3. If unreadable, mark `[UNCLEAR]` — never guess.
4. Image paths are **flat** in `data/` — no subdirectories.
5. Always check image dimensions before reading (2000 px limit).
6. **Always commit and push** before ending a session.
7. **Never read more than 100 images** in one context (API limit).
8. **Document WIP** in `.claude/*.md` for session continuity.

Full accept/reject + do/don't tables: [`.claude/standards/GUARDRAILS.md`](.claude/standards/GUARDRAILS.md).

---

## Quick Reference Commands

```bash
# Image status before reading
python scripts/image_safeguards.py status

# Validate after changes
python scripts/validate-recipes.py

# Process oversized images
python scripts/process_images.py
```

---

## Adding a New Recipe (summary)

1. Add image to `data/` (flat).
2. Process: `python scripts/process_images.py`.
3. Transcribe using `data/processed/<file>`.
4. Add JSON to `data/recipes_master.json`.
5. Validate: `python scripts/validate-recipes.py`.
6. Rebuild indexes: `python scripts/build-ingredient-index.py`.

Full workflow in [`.claude/MAINTENANCE.md`](.claude/MAINTENANCE.md).

---

## Version History

| Version | Date | Changes |
|---|---|---|
| 2.1 | 2026-05-10 | Added `SKILLS.md` skill index. CLAUDE.md references it. |
| 2.0 | 2026-05-01 | Lean hub restructure. Extracted OCR / image / schema / guardrails / hub-aggregation subfiles into `.claude/standards/`. CLAUDE.md cut from ~394 lines to ~150. |
| 1.4 | 2026-01 | Added Family Repositories table, Routine Maintenance, MAINTENANCE.md |
| 1.3 | 2026-01 | Added skills, skill-rules.json, MCP docs, cross-repo standards |
| 1.2 | 2026-01 | Added .claude/ hooks, OCR correction standards, measurement standardization |
| 1.1 | 2026-01 | Added Quick Start, Priority Framework, Guardrails |
| 1.0 | — | Original CLAUDE.md |

---

*"She looketh well to the ways of her household, and eateth not the bread of idleness."* — Proverbs 31:27

---

## Cognitive Memory — Slice 6 Observation Capture

To enable always-on cognitive memory observation capture in this repo, register the canonical hook (lives in `ken`) in `.claude/settings.json`:

```json
"env": {
  "MEMORY_OBSERVATIONS_ENABLED": "true",
  "MEMORY_AUTO_OBSERVE_ENABLED": "true"
},
"hooks": {
  "PostToolUse": [
    {
      "matcher": "*",
      "hooks": [
        {"type": "command",
         "command": "/home/user/ken/.claude/hooks/observe-tool-use.sh"}
      ]
    }
  ]
}
```

Hook is **fail-closed**: any error → exit 0, never blocks the tool call. Args SHA256-hashed via `_compute_args_hash` before disk; raw values never persisted. Errors → `/tmp/observe-hook.err`. Surface candidates: call `memory_ops.extract_candidates_from_observations(session_id)` after a session.

Setup memory: id `5a9c8ae1` (recall via `python3 /home/user/ken/orchestrator/memory_ops.py recall "Slice 6 always-on cognitive memory observation capture"`). Currently active in `ken/.claude/settings.json` (commit `ca78cad`); per-repo activation is opt-in via the absolute-path reference above.
