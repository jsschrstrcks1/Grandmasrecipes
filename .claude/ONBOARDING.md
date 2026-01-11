# Claude Code Infrastructure Update — Onboarding

This repository has been enhanced with Claude Code infrastructure. Here's what's new:

---

## CLAUDE.md Updates (v1.0 → v1.4)

The main instruction file has been significantly expanded:

| Section | Purpose |
|---------|---------|
| **Quick Start** | 30-second essentials (6 rules) |
| **Priority Framework** | Decision-making hierarchy |
| **Family Repositories** | GitHub URLs for all family repos |
| **Routine Maintenance** | Quick checklists for common tasks |
| **OCR Correction Standards** | Character confusion, measurement checks |
| **Guardrails** | Accept/Reject table for clarity |
| **Do's and Don'ts** | Expanded actionable lists |
| **Version History** | Change tracking |

---

## New `.claude/` Directory

```
.claude/
├── settings.json           # Hook configuration
├── skill-rules.json        # Skill auto-activation (3 skills)
├── ONBOARDING.md           # THIS FILE
├── MAINTENANCE.md          # Detailed maintenance workflows
├── CROSS_REPO_STANDARDS.md # Cross-repo sync standards
├── mcp-servers.md          # MCP server integration docs
├── hooks/
│   ├── post-write-validate.sh   # Runs after Edit/Write
│   └── image-safety-check.sh    # Runs before Read on images
└── skills/
    ├── recipe-transcription/SKILL.md  # OCR workflow
    └── recipe-validation/SKILL.md     # Schema validation
```

---

## Automatic Hooks

These run automatically based on `settings.json`:

| Hook | Trigger | What It Does |
|------|---------|--------------|
| `post-write-validate.sh` | Edit\|Write on recipe files | Runs `validate-recipes.py`, shows errors |
| `image-safety-check.sh` | Read on image files | Warns if image may exceed 2000px |

---

## Skills (Auto-Activate via `skill-rules.json`)

| Skill | Activates When | Loads |
|-------|----------------|-------|
| `recipe-transcription` | Reading images, keywords: transcribe, OCR, handwritten | `.claude/skills/recipe-transcription/SKILL.md` |
| `recipe-validation` | Editing recipes, keywords: validate, check, schema | `.claude/skills/recipe-validation/SKILL.md` |
| `image-safety` | Reading images in `data/` | Rule-based warnings |

---

## Key Documentation Files

**Read in this order:**
1. `CLAUDE.md` — Main instructions (always read first)
2. `.claude/MAINTENANCE.md` — Detailed task workflows
3. `.claude/skills/*/SKILL.md` — Skill-specific guidance (auto-loaded)

**Reference as needed:**
- `.claude/CROSS_REPO_STANDARDS.md` — When syncing across family repos
- `.claude/mcp-servers.md` — When integrating MCP servers

---

## What Changed

### Hooks Now Auto-Run
- Recipe validation triggers after any edit to recipe files
- Image size warnings trigger before reading images

### Skills Provide Context
- Transcription skill loads OCR correction tables and confidence ratings
- Validation skill loads schema requirements and error fixes

### Maintenance Documented
- Step-by-step workflows for adding recipes, images, deployment
- Script reference with usage examples
- Common error troubleshooting

### Cross-Repo Standards
- GitHub URLs for all family repositories
- Shared schema, categories, measurement formats
- Sync checklist for keeping repos aligned

---

## Quick Verification

```bash
# Check hooks are configured
cat .claude/settings.json | python -c "import json,sys; print('Hooks OK' if json.load(sys.stdin).get('hooks') else 'No hooks')"

# Check skills are defined
cat .claude/skill-rules.json | python -c "import json,sys; d=json.load(sys.stdin); print(f'{len(d[\"skills\"])} skills defined')"

# Verify skill files exist
ls .claude/skills/*/SKILL.md
```

---

## When Working on This Repo

1. **Read `CLAUDE.md`** — Contains all core rules and quick reference
2. **Let hooks run** — They provide automatic validation and warnings
3. **Check skill guidance** — When transcribing or validating, skills auto-load context
4. **Use maintenance workflows** — `.claude/MAINTENANCE.md` has step-by-step guides

---

## Quick Reference

### Priority Framework

| Priority | Principle |
|----------|-----------|
| 1 | **Accuracy-First** — Never guess or invent |
| 2 | **Preservation-First** — Handwritten images are sacred |
| 3 | **Fidelity-First** — Preserve grandma's exact wording |
| 4 | **Readability-First** — Family needs usable recipes |

### Non-Negotiables

- **NEVER** delete handwritten images
- **NEVER** invent ingredients, steps, or measurements
- **ALWAYS** use `[UNCLEAR]` for uncertain text
- **ALWAYS** validate after making changes
- Images are **FLAT** in `data/` — no subdirectories

### Common Commands

```bash
python scripts/image_safeguards.py status  # Before reading images
python scripts/validate-recipes.py          # After editing recipes
python scripts/process_images.py            # After adding images
python scripts/build-ingredient-index.py    # Before deployment
```

---

*Last updated: 2026-01*
