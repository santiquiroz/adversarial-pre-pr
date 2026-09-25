# Default checklist (uncalibrated)

Used when no `checklist.local.md` exists next to `SKILL.md`. The order follows the finding frequency of one real calibration (see `references/catalog-dotnet-angular.md`); once you calibrate against your own bot, write your version to `checklist.local.md` ordered by YOUR frequencies.

Each category states the mechanism in stack-agnostic terms. Lines marked *.NET/Angular example* are illustrations from that calibration — translate them to your stack.

1. **Input validation**: collection parameters checked for null/empty before processing; required fields enforced at the boundary (forms, DTOs, persisted string lengths); values validated before being interpolated into URLs, queries or paths; input never mapped straight onto a persisted entity.
   - *.NET/Angular example:* new `FormControl` without `Validators` on a required field; entity string property without `StringLength`.
2. **Null-safety**: results of "find/first-or-default" lookups checked before member access; no unchecked casts or unwraps of nullable values; arguments verified before being passed deeper.
   - *.NET/Angular example:* `FirstOrDefaultAsync(...)` result dereferenced without a null check.
3. **Error handling**: persistence and transactional calls wrapped so failures are handled, not swallowed; resources and transactions released on exception; async chains have a failure path; errors logged with context.
   - *.NET/Angular example:* `SaveChangesAsync` outside try/catch; transaction not under `await using`; Angular promise without `.catch`.
4. **Persistence / ORM usage**: multi-step writes inside one transaction; direct deletes instead of fetch-then-delete; schema changes (new tables, columns, relations) accompanied by a migration; cascade/delete behavior and column defaults chosen deliberately, not by omission.
   - *.NET/Angular example:* new `DbSet` or navigation property without a migration; FK `OnDelete` left at NO ACTION by default.
5. **Signature drift**: when a function, method or interface changes, update ALL call sites across the whole repo (tests, mocks, handlers, interfaces); declared return types match implementations.
6. **Tests**: assert the actual effect, not just "does not throw"; failure tests check the concrete error; shared mocks/fixtures reset between tests; no magic test data (use constants or factories).
   - *.NET/Angular example:* `[SetUp]` that does not reset every mock.
7. **Visibility and modifiers**: access level, inheritance and overridability chosen deliberately, as narrow as possible.
   - *.NET/Angular example:* C# `private`/`sealed`/`virtual`.
8. **Framework lifecycle and UI state**: timers, subscriptions and listeners released on teardown; API-hitting inputs debounced; keys/enums kept in sync with the structures that consume them; declared state actually consumed; async loads never silently clear user-entered or persisted values.
   - *.NET/Angular example:* stored `setTimeout` without `clearTimeout` in `ngOnDestroy`; signal declared but never read.
9. **Security**: authorization never commented out or bypassed; shared mutable state safe under concurrency; anything that WIDENS a permission or data scope is HIGH severity, always.
