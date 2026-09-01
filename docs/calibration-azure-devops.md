# Calibrating from Azure DevOps PR threads

Goal: extract every comment your AI reviewer has posted, categorize by mechanism, count frequencies, and separate provable false positives.

## 1. Identify the reviewer

AI review extensions post as the project's build service identity (e.g. `<Project> Build Service (<Org>)`) and usually prefix comments with a fixed marker (e.g. `[AI PR Review]`). Open a recent PR and note both.

## 2. Pull the threads

```bash
ORG="https://dev.azure.com/<your-org>"
TOKEN=$(az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798 --query accessToken -o tsv)

curl -s -H "Authorization: Bearer $TOKEN" \
  "$ORG/<project>/_apis/git/repositories/<repo>/pullRequests/<prId>/threads?api-version=7.0" \
  > pr-<prId>-threads.json
```

Repeat for your 5-10 most recent PRs. Filter comments whose author matches the reviewer identity and whose content starts with its marker. Keep: file path, line, full text, thread status (`active` / `fixed` / `wontFix`).

## 3. Find the mechanism and the config

- **Extension?** `GET $ORG/_apis/extensionmanagement/installedextensions?api-version=7.1-preview.1` — look for review-related publishers. Some extensions keep their rule store in extension data (`_apis/ExtensionManagement/InstalledExtensions/<publisher>/<ext>/Data/...`) — read it: the configured prompt often differs from what the bot actually posts, and cited rule IDs may not exist.
- **Pipeline task?** grep your repo's pipeline YAML for review tasks; note the trigger (per push?).
- **Branch policies:** `GET $ORG/<project>/_apis/policy/configurations?api-version=7.0` — find what actually blocks: comment-resolution policy, build validation, or a vote. This determines how threads must be resolved.

## 4. Categorize

Bucket every comment by MECHANISM (what code pattern triggered it), not by wording. Typical buckets: input validation, null-safety, error handling, ORM/transactions, signature drift between tests and production, test asserts, language modifiers, framework-specific (UI), security. Count per bucket; sort your checklist by count.

## 5. Separate provable false positives

A false positive qualifies ONLY with proof: the compiler accepts the flagged syntax, the file is auto-generated, the cited rule doesn't exist in the store, or the bot contradicts itself between runs. Write the proof next to each class — that text becomes your honest thread-resolution reply.

## 6. Record operational behavior

- Does it dedupe across runs? (Many don't — every push re-posts. Batch your pushes.)
- Does it comment on generated files even when its own prompt excludes them?
- Does it vote, or block only via comment resolution?

Fold all of this into your copy of the skill.
