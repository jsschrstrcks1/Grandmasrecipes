# Skills — Grandmasrecipes

> The toolkit grandmother. Recipe-domain skills for transcription/validation; the smart converters (diabetic, heart-smart, milk, protein, scaling) live as JavaScript modules in the repo root rather than as skills.

This document is the human-facing index of all Claude Code skills configured in this repository. The agent-facing pointer lives in [`CLAUDE.md`](CLAUDE.md). Skills follow the agent-skills-spec format and live under `.claude/skills/`.

**Total skills configured: 18.** 16 are the standard household kit; 2 are recipe-domain specific.

---

## Quick reference

| Skill | Activation | Default | Domain |
|---|---|---|---|
| [`recipe-transcription`](#recipe-transcription) | automatic on image+recipe context | on | Recipe ingestion |
| [`recipe-validation`](#recipe-validation) | automatic before commit | on | Recipe integrity |
| Standard household kit (16 skills) | mixed | on | See [section below](#standard-household-kit) |

**Note:** The five smart converters (`diabetic-converter.js`, `heart-smart-converter.js`, `milk-substitution.js`, `protein-substitution.js`, `scaling-intelligence.js`) ship as **JavaScript modules**, not Claude Code skills. They run in the browser. Their refusal logic ("refuse and explain when conversion would fundamentally change the recipe") is documented in the README under [Smart converters](README.md#smart-converters).

---

## How invocation works

Claude Code skills can fire three ways:

**1. Automatic activation** via YAML `keywords:` and surrounding context.

**2. Explicit invocation:**

```
"Use the recipe-transcription skill to extract this Tampa Tribune clipping."
/skill recipe-transcription
```

**3. Implicit invocation by task shape** — image reads, recipe JSON edits, completion claims, web fetches.

**Disabling for a session:** "For this session, do not apply X."

---

## Recipe-domain skills

### `recipe-transcription`

**Path:** `.claude/skills/recipe-transcription/SKILL.md`

Extracts structured recipe data from images. This corpus is small (5 recipes at last count) but each one has documented known-issues; transcription accuracy matters.

**Activation:** automatic when image-source-of-recipe context is detected, or explicit.

**Non-negotiables enforced by this skill:**

- Never invent ingredients, steps, temperatures, times, or yields
- Mark unclear text `[UNCLEAR]`
- Preserve original spelling verbatim (e.g., "Jubilie Jumbles" stays "Jubilie")
- Keep family attributions
- Always read from `data/processed/`, never raw oversized images
- Image paths are FLAT in `data/`; subdirectories do not exist

**Example prompts that should trigger:**

| Prompt | Expected behavior |
|---|---|
| "Transcribe `data/processed/Grandmas-recipes - 12.jpeg`" | Reads processed copy, marks `[UNCLEAR]` for ambiguous OCR |
| "Add the Glazed Carrots clipping" | Verifies source attribution; transcribes; sets confidence |
| "Process the new card scan in `data/grandma/`" | Refuses — path is wrong; subdirectory doesn't exist |

### `recipe-validation`

**Path:** `.claude/skills/recipe-validation/SKILL.md`

Validates `data/recipes_master.json` against the schema. Plus: validates the cross-repo aggregation contract (`HUB_AGGREGATION.md`).

**Activation:** automatic before commit; also explicit.

**Validation rules enforced:**

- Required fields: `id`, `title`, `ingredients[]`, `instructions[]`
- Slug uniqueness
- Image references resolve
- Category vocabulary
- `confidence.flags[]` populated when `confidence.overall == "low"`
- Original spelling preserved

**Manual invocation:**

```
python scripts/validate-recipes.py
```

---

## Cross-repo aggregator (this repo's special role)

`Grandmasrecipes` doubles as the hub that aggregates from all four family recipe repos. The aggregation logic lives in `script.js` (174 KB) and consumes data from sister repos via Pages URLs:

| Collection | Pages site | Collection ID |
|---|---|---|
| Grandma Baker | jsschrstrcks1.github.io/Grandmasrecipes | `grandma-baker` |
| MomMom Baker | jsschrstrcks1.github.io/MomsRecipes | `mommom-baker` |
| Granny Hudson | jsschrstrcks1.github.io/Grannysrecipes | `granny-hudson` |
| Other Recipes | jsschrstrcks1.github.io/Allrecipes | `all` |

The contract is documented in `.claude/standards/HUB_AGGREGATION.md`. When modifying the aggregator, the standard household kit's `verification-before-completion` skill should fire before any "works" claim — actually load the cross-repo aggregator and confirm all four collections render.

---

## Standard household kit

Common to every sister repo. Canonical versions live in `ken/.claude/skills/`.

| Skill | Activation | One-line |
|---|---|---|
| `brainstorming` | automatic on creative work | Pre-implementation creative exploration. |
| `cognitive-memory` | automatic on session start | Cross-session knowledge persistence. Memory scope: `/Grandmasrecipes`. |
| `executing-plans` | explicit | Use when executing a written plan. |
| `finishing-a-development-branch` | explicit | Decide merge / PR / cleanup. |
| `prompt-optimizer` | automatic on prompt-improvement requests | Optimizes raw prompts. Advisory only. |
| `receiving-code-review` | explicit | Use when receiving review feedback. |
| `requesting-code-review` | explicit | Use when completing tasks before merging. |
| `safety-guard` | automatic on destructive ops | Prevents destructive operations. |
| `security-review` | automatic on auth/secrets/payment | Security checklist + patterns. |
| `security-scan` | explicit | Scans `.claude/` config. |
| `session-checkpoint` | automatic + explicit | Atomic commits, checkpoint summaries, rate-limit recovery. |
| `subagent-driven-development` | explicit | Implementation plans with independent tasks. |
| `systematic-debugging` | automatic on bug/test-failure | Use before proposing fixes. |
| `using-git-worktrees` | explicit | Isolate feature work. |
| `verification-before-completion` | automatic on completion claims | Refuses "complete/fixed/passing" without observed output. |
| `writing-plans` | explicit | Use when you have a spec for a multi-step task. |

---

## Multi-LLM orchestrator

This repo defaults to **`recipe` mode** in the orchestrator hosted in [ken](https://github.com/jsschrstrcks1/ken). Lead model: GPT.

| Slash command | Usage |
|---|---|
| `/consult` | `/consult gpt structure "review this Jubilie Jumbles transcription"` |
| `/orchestrate recipe "<task>"` | Full pipeline: transcribe → validate → integrate |

First-time setup per session:

```bash
pip3 install -q -r /home/user/ken/orchestrator/requirements.txt
```

---

## See also

- [`CLAUDE.md`](CLAUDE.md) — agent context
- [`README.md`](README.md) — public-facing overview, including converter documentation
- [`PLAN-nutrition-facts.md`](PLAN-nutrition-facts.md) — nutrition-facts integration plan
- [`.claude/standards/`](.claude/standards/) — OCR, IMAGE_WORKFLOW, RECIPE_SCHEMA, GUARDRAILS, HUB_AGGREGATION
- `ken` — hosts the orchestrator; canonical versions of the standard household kit
