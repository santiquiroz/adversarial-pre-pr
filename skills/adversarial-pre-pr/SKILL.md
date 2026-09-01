---
name: adversarial-pre-pr
description: Use when about to push commits or create/update a pull request on a repo guarded by an automated AI reviewer (Azure DevOps AI review extensions, CodeRabbit, pr-agent, Copilot review) — runs an adversarial local review calibrated on that reviewer's real findings and FIXES them before pushing
---

# Adversarial Pre-PR Review

## Overview

Many teams run an automated AI reviewer in their PR pipeline. These bots block completion (via comment-resolution policies or required checks), often re-post findings on every push, and mix real catches with recurring false positives.

**Purpose: arrive at the PR with the code already fixed.** This is an adversarial quality gate, not a bypass mechanism. Honesty rule: a finding may only be dismissed as a false positive when it can be PROVEN (valid syntax verifiable by the compiler, auto-generated file, nonexistent rule); everything else gets fixed.

This skill ships with an example catalog for .NET + Angular (see `examples/`). Calibrate your own from your reviewer's actual comments — `docs/calibration-azure-devops.md` shows how.

## Phase 1 — Find (adversarial)

1. Diff under review: `git diff <target-branch>...HEAD`. Only files in the diff — EXCEPTION: for "method signature drift", grep call sites across the WHOLE repo.
2. Act as the harshest reviewer possible: apply your calibrated checklist AND genuine best practices the checklist doesn't cover. Read the full flow of touched components — functional regressions never come from checklists alone.
3. Per-finding format: `file:line — [category][HIGH|MEDIUM|LOW] finding — proposed fix`. Line = new side of the diff (HEAD). Category = mechanism; severity = impact (a permission-scope regression found via a UI checklist item is HIGH).
4. Report in TWO blocks: **Actionable** and **Provable false positives** (each with its proof, not an excuse).

## Phase 2 — Fix

- Fix ALL actionable findings, in severity order, before any push. Large fixes get delegated with exact instructions; nothing is postponed "for another PR" without an explicit, recorded decision.
- Mandatory final step: run the project's build + full test suites for every side the diff touches. Inspection never replaces the run.
- One single push with everything: bots that run per-push re-post findings each time — batching means fewer threads and less noise.

## Calibrating your catalog

1. Mine your reviewer's real comments (for Azure DevOps: PR threads REST API — see `docs/calibration-azure-devops.md`).
2. Categorize by MECHANISM (null-safety, input validation, error handling, ORM usage, signature drift, test asserts, framework-specific) and count frequency.
3. Order your checklist by real frequency — review passes become efficient because you look for what the bot actually finds.
4. Separate recurring PROVABLE false positives into their own table, each with its proof written down (so thread resolution is honest and fast).
5. Record the bot's operational behavior: does it dedupe? does it vote or block via comment policy? does it comment on generated files? This changes your push strategy.

## Known false-positive classes (from real-world calibration)

| Bot comment pattern | Typical proof |
|---|---|
| Flags modern language syntax as invalid (e.g. C# 12 primary constructors) | Compiles; official language feature |
| Enforces a naming convention your repo doesn't use | Repo-wide consistency of the actual convention |
| Comments on auto-generated files (ORM migrations, API client proxies) | Hand-edits are lost on next regeneration |
| Cites rule IDs that don't exist in its own rule store | Rule store inspection |
| Contradicts itself between runs on the same file | Both comments quoted side by side |

## Red flags — you're bypassing, not reviewing

- Writing a wontFix justification you couldn't defend to the bot's vendor.
- Dismissing a finding because fixing it is tedious.
- Skipping the test-suite run because "the diff is small".
- Postponing an actionable HIGH to "a future PR" without recording it.

All of these mean: go back to Phase 2 and fix.
