# adversarial-pre-pr

An agent skill (Claude Code / compatible harnesses) that runs an **adversarial code review locally, before you push a PR**, calibrated on what your pipeline's AI reviewer actually flags — and **fixes the findings** instead of arguing with the bot.

## Why

Automated AI reviewers in PR pipelines (Azure DevOps review extensions, CodeRabbit, pr-agent, Copilot review) are useful but noisy:

- They block PR completion via comment-resolution policies.
- Many re-post findings on **every push** — a PR can accumulate 100+ comments in a day.
- They mix real catches with recurring, provable false positives.

The usual reactions are bad: ignoring the bot, or gaming it. This skill takes the third path: **run the same review locally first, fix what's real, and document proof for what isn't.**

## What it does

1. **Find** — reviews your diff as the harshest reviewer possible, using a checklist ordered by your bot's REAL finding frequency, plus genuine best practices beyond the checklist.
2. **Fix** — everything actionable, in severity order, verified by your build + full test suites, batched into a single push.
3. **Prove** — recurring false positives get a proof table (compiler evidence, auto-generated file, nonexistent rule id), so resolving those threads is honest and takes seconds.

It is explicitly NOT a bypass tool. The skill's red-flags section treats "dismissing a finding because fixing is tedious" as a violation.

## Install

Copy `skills/adversarial-pre-pr/` into your skills directory:

```bash
# Claude Code
cp -r skills/adversarial-pre-pr ~/.claude/skills/

# Cross-runtime (Codex, Copilot CLI, Gemini CLI)
cp -r skills/adversarial-pre-pr ~/.agents/skills/
```

Then, before pushing to a branch with a PR: invoke `/adversarial-pre-pr`.

## Calibrate it for YOUR bot

The generic skill works out of the box, but the value multiplies when you calibrate:

1. Mine your reviewer's real comments — [references/calibration-azure-devops.md](skills/adversarial-pre-pr/references/calibration-azure-devops.md) walks through the Azure DevOps PR-threads REST API.
2. Categorize findings by mechanism, count frequencies, reorder the checklist.
3. Build your provable-false-positive table.

See [references/catalog-dotnet-angular.md](skills/adversarial-pre-pr/references/catalog-dotnet-angular.md) for a real calibration result (anonymized): 219 bot comments distilled into 9 categories with frequencies, plus the false-positive classes that emerged.

## Field results

First real run of the calibrated skill (on a diff that had already passed two other AI reviews) found 4 real bugs, including a HIGH-severity silent permission-scope regression, before the pipeline bot ever saw the code.

## License

MIT
