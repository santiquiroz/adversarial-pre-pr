---
name: adversarial-pre-pr
description: Use when about to push commits or create/update a pull request on a repo guarded by an automated AI reviewer (Azure DevOps AI review extensions, CodeRabbit, pr-agent, Copilot review) — runs an adversarial local review calibrated on that reviewer's real findings and FIXES them before pushing
---

# Adversarial Pre-PR Review

## Overview

Many teams run an automated AI reviewer in their PR pipeline. These bots block completion (via comment-resolution policies or required checks), often re-post findings on every push, and mix real catches with recurring false positives.

**Purpose: arrive at the PR with the code already fixed.** This is an adversarial quality gate, not a bypass mechanism. Honesty rule: a finding may only be dismissed as a false positive when it can be PROVEN (valid syntax verifiable by the compiler, auto-generated file, nonexistent rule); everything else gets fixed.

This skill ships with an example catalog for .NET + Angular (see `references/catalog-dotnet-angular.md`). Calibrate your own from your reviewer's actual comments — `references/calibration-azure-devops.md` shows how.

## Phase 1 — Find (adversarial)

1. Diff under review: `git fetch origin <target>` then `git diff origin/<target>...HEAD` (a stale local target branch yields the wrong merge-base), plus `git diff HEAD` and `git status --short` for uncommitted/untracked work — review it too, but warn that the PR won't see it until it is committed. Only files in the diff — EXCEPTION: for "method signature drift", grep call sites across the WHOLE repo.
2. Pick the checklist: `checklist.local.md` next to this file if it exists (your calibration; also read `false-positives.local.md` if present), otherwise the default `checklist.md`.
3. Act as the harshest reviewer possible: apply that checklist AND genuine best practices the checklist doesn't cover. Read the full flow of touched components — functional regressions never come from checklists alone.
4. Per-finding format: `file:line — [category][HIGH|MEDIUM|LOW] finding — proposed fix`. Line = new side of the diff (HEAD). Category = mechanism; severity = impact (a permission-scope regression found via a UI checklist item is HIGH).
5. Report in TWO blocks: **Actionable** and **Provable false positives** (each with its proof, not an excuse).

## Phase 2 — Fix

- Record the starting point first: `git rev-parse HEAD` → `<pre-fix-sha>`.
- Fix ALL actionable findings, in severity order, before any push. Large fixes get delegated with exact instructions; nothing is postponed "for another PR" without an explicit, recorded decision.
- Re-run Phase 1 on your own fixes (`git diff <pre-fix-sha>` covers committed and uncommitted ones) — the bot reviews them in the same push. Repeat until a pass yields no new actionable finding.
- Mandatory final step: run the project's build + full test suites for every side the diff touches. Inspection never replaces the run.
- One single push with everything: bots that run per-push re-post findings each time — batching means fewer threads and less noise.

## Calibrating your catalog

1. Mine your reviewer's real comments (for Azure DevOps: PR threads REST API — see `references/calibration-azure-devops.md`).
2. Categorize by MECHANISM (null-safety, input validation, error handling, ORM usage, signature drift, test asserts, framework-specific) and count frequency.
3. Order your checklist by real frequency and save it as `checklist.local.md` next to this file (git-ignored; it replaces `checklist.md`) — review passes become efficient because you look for what the bot actually finds.
4. Separate recurring PROVABLE false positives into their own table in `false-positives.local.md`, each with its proof written down (so thread resolution is honest and fast).
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
