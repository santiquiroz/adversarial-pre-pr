# Example calibration: .NET 10 minimal API + EF Core + Angular

Result of mining 219 real comments from an Azure DevOps AI review extension (gpt-4o-mini based) across 4 PRs of a production codebase. Anonymized.

## Checklist (ordered by real frequency)

1. **Input validation (46/219)**: collection parameters not null/empty before processing; new Angular FormControls with `Validators` when the field is required; emails validated before URL interpolation; entity string properties with `StringLength`/`required`; never map input straight onto an entity without validation.
2. **Null-safety (42)**: `FirstOrDefault(Async)`/`Find` results null-checked before member access; no casting nullables without checking; parameters verified before passing to private methods.
3. **Error handling (33)**: try/catch around `SaveChangesAsync`/transactional repositories; transactions disposed on exception (`await using`); Angular promises with `.catch`; errors logged.
4. **EF Core (30)**: multi-step operations inside a transaction; direct delete instead of fetch-then-delete; new `DbSet` configured; new navigation property accompanied by a migration; FK `OnDelete` behavior chosen DELIBERATELY (don't accept NO ACTION by omission); new columns with thought-out defaults/constraints.
5. **Method-signature drift (26)** — the most repeated real catch: when a service signature changes, update ALL call sites (test mocks, endpoints, interface); interface return type == implementation.
6. **Tests (22)**: assert the actual effect (not just "doesn't throw"); exception tests verify the concrete exception; `[SetUp]` resets all mocks; no hardcoded data (constant or factory).
7. **C# modifiers (14)**: deliberate `private`/`sealed`/`virtual`.
8. **Angular**: `clearTimeout` in `ngOnDestroy` for every stored `setTimeout`; debounce on filters that hit the API; union-type keys in sync with column-definition arrays; declared signals actually consumed; async loads must never silently clear user/persisted form values.
9. **Security (5)**: never leave authorization commented out; thread-safety of shared fixture state; anything that WIDENS a permission scope is HIGH severity, always.

## Provable false-positive classes that emerged

| Bot comment | Proof |
|---|---|
| "The class constructor should not have parentheses" | C# 12 primary constructors — compiles; official syntax |
| Test names "should include 'Should' or 'When'" | Repo-wide convention is `Method_Result_Condition` |
| Findings on `Migrations/*.Designer.cs`, `*ModelSnapshot.cs`, generated API proxies | Auto-generated (EF / NSwag); hand-edits lost on regeneration |
| "Rule violation (`uuid-...`)" linking to a rule id | The extension's rule store contained exactly one rule; ids were hallucinated |
| "PK on non-unique column" | Misreading of the EF model snapshot; actual PK is another column |
| Migration "should be partial" / "should be public" (contradictory between runs) | Standard EF Core generated template |

## Operational behavior observed

- No dedup across runs: every push re-posted 3-10 findings; one PR reached 137 comments in ~24h. Countermeasure: batch fixes into one push.
- Commented on generated files even though its own configured prompt excluded them.
- Never voted or rejected: blocked indirectly through a comment-resolution branch policy. Thread outcomes used: `fixed` or `wontFix` (with proof).
- The configured prompt requested structured Spanish output with severities; the bot actually emitted unstructured English one-liners. Calibrate on what it POSTS, not on what it's configured to do.

## Field result

First calibrated run, on a diff that had already passed two other AI reviews, found 4 real bugs before the pipeline bot saw the code — including a HIGH silent permission-scope regression (an async load cleared a form value, widening a saved permission from "one asset" to "all assets").
