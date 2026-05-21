#!/usr/bin/env python3
"""
Hand-merge artifact for PR #69 (review-repo-status: audit reports + 234 file renames).

PR #69 does two distinct things:
  1. Adds 2 audit reports under .claude/:
       - .claude/HEALTH_AUDIT_REPORT.md (243 lines, dated 2026-01-30)
       - .claude/REPO_STATUS_REVIEW.md (216 lines, dated 2026-02-05)
  2. Renames 232 image files out of `data/unscanned recipe books/` into `data/`
     (flat structure, per CLAUDE.md image-path rule).

This script handles part 1 (audit reports — clean adds, no conflict).
For part 2 (renames) it generates a list you can pipe to `git mv` locally.

WHY MANUAL:
PR #69 was opened against an older main (`685f5b18`). Since then the cognitive-
memory PR + claude-mem-eval PR + my README trim merged. None of those touched
the audit-report files or the renamed images, but GitHub's auto-merge gave up
because of metadata changes in the .claude/ tree. Doing it manually avoids
the risk.

REQUIREMENTS:
  - Run from inside the Grandmasrecipes repo on current main
  - PR #69's branch fetched: `git fetch origin claude/review-repo-status-6VORt`
  - Or fetch by SHA: 6343344b250be7dd8777ddd723e97e5ce2a97aa7

HOW TO APPLY:
  cd <Grandmasrecipes repo>
  git fetch origin claude/review-repo-status-6VORt

  # Step 1: drop the audit reports (this script does it)
  python3 scripts/_merge_artifacts/apply_pr69_merge.py --reports

  # Step 2: print the rename plan
  python3 scripts/_merge_artifacts/apply_pr69_merge.py --renames

  # Step 3: review and execute the renames yourself with `git mv`
  python3 scripts/_merge_artifacts/apply_pr69_merge.py --renames --execute

  # Step 4: validate + commit
  python3 scripts/validate-recipes.py
  git add .claude/HEALTH_AUDIT_REPORT.md .claude/REPO_STATUS_REVIEW.md data/
  git commit -m "Merge PR #69: audit reports + image flattening (manual)"

  # Then close PR #69 with comment linking to this commit.
"""

import argparse
import subprocess
import sys
from pathlib import Path

PR69_HEAD_SHA = '6343344b250be7dd8777ddd723e97e5ce2a97aa7'

AUDIT_REPORTS = [
    '.claude/HEALTH_AUDIT_REPORT.md',
    '.claude/REPO_STATUS_REVIEW.md',
]

# The rename pattern: every file under "data/unscanned recipe books/" moves
# to "data/" with the same basename. PR #69 has 232 such renames. Rather than
# hardcode them, we discover them at runtime by listing the source directory.
SOURCE_DIR = Path('data/unscanned recipe books')
DEST_DIR = Path('data')


def git_show(ref_path: str) -> bytes:
    """Read a file from a git ref (returns bytes for binary safety)."""
    try:
        return subprocess.check_output(
            ['git', 'show', f'{PR69_HEAD_SHA}:{ref_path}'],
        )
    except subprocess.CalledProcessError:
        print(
            f'ERROR: could not read {ref_path} from PR #69 head.\n'
            '  Did you fetch? git fetch origin claude/review-repo-status-6VORt',
            file=sys.stderr,
        )
        sys.exit(1)


def apply_reports(repo_root: Path, dry: bool):
    """Drop the two audit reports into .claude/."""
    print('=== Audit reports ===')
    for path in AUDIT_REPORTS:
        target = repo_root / path
        if target.exists():
            print(f'SKIP {path} (already exists on main — review manually)')
            continue
        content = git_show(path)
        if dry:
            print(f'  [DRY] would write {path} ({len(content)} bytes)')
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            print(f'  + {path} ({len(content)} bytes)')


def plan_renames(repo_root: Path, execute: bool):
    """Generate `git mv` plan for the 232 image renames."""
    src_root = repo_root / SOURCE_DIR
    if not src_root.exists():
        print(f'NOTE: {SOURCE_DIR} does not exist on main — renames already applied?')
        return
    files = sorted(p.name for p in src_root.iterdir() if p.is_file())
    print(f'\n=== Renames ({len(files)} files) ===')
    for name in files:
        src = SOURCE_DIR / name
        dst = DEST_DIR / name
        if (repo_root / dst).exists():
            print(f'  CONFLICT: {dst} already exists — skip {src}')
            continue
        if execute:
            subprocess.run(['git', 'mv', str(src), str(dst)], check=True, cwd=repo_root)
            print(f'  mv {src}  →  {dst}')
        else:
            print(f'  git mv "{src}" "{dst}"')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--reports', action='store_true', help='Drop the 2 audit reports')
    p.add_argument('--renames', action='store_true', help='Show the rename plan')
    p.add_argument('--execute', action='store_true', help='Actually run git mv (only with --renames)')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()

    if not (args.reports or args.renames):
        p.print_help()
        sys.exit(0)

    repo_root = Path(__file__).resolve().parents[2]
    if args.reports:
        apply_reports(repo_root, dry=args.dry_run)
    if args.renames:
        plan_renames(repo_root, execute=args.execute and not args.dry_run)


if __name__ == '__main__':
    main()
