# Calibrating from Azure DevOps PR threads

Goal: extract every comment your AI reviewer has posted, categorize by mechanism, count frequencies, and separate provable false positives.

## 1. Identify the reviewer

AI review extensions post as the project's build service identity (e.g. `<Project> Build Service (<Org>)`) and usually prefix comments with a fixed marker (e.g. `[AI PR Review]`). Open a recent PR and note both.

## 2. Pull the threads

```bash
ORG="https://dev.azure.com/<your-org>"
AUTH="Authorization: Bearer $(az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798 --query accessToken -o tsv)"

fetch_json() {
  local url="$1" out="$2" code
  code=$(curl -sS --fail-with-body -H "$AUTH" -o "$out" -w '%{http_code}' "$url")
  if [ "$code" != "200" ]; then
    echo "HTTP $code from $url - response discarded (203 = sign-in page, see below)" >&2
    rm -f "$out"
    return 1
  fi
}

fetch_json "$ORG/<project>/_apis/git/repositories/<repo>/pullRequests/<prId>/threads?api-version=7.0" "pr-<prId>-threads.json"
```

`--fail-with-body` (curl 7.76+) only rejects 4xx/5xx, so the explicit `200` check is what protects you from the common failure: when Azure DevOps stops accepting the `az` session it answers **HTTP 203 with its HTML sign-in page**. That is a 2xx, so a plain `curl -s ... > file` saves HTML and step 4 counts garbage. It can happen with a token that has not expired, and in long-running scripts once the token (valid about one hour) does expire. Fix it with an interactive `az login` and rebuild `AUTH`; in long loops, fetch a fresh token instead of reusing the first one.

**Alternative: a personal access token.** A PAT with scope **Code (Read)** is enough for PR threads (a Code-only PAT gets 401 on work items and builds). Send it as Basic auth with an empty user name, read it without echoing, and never write it to a file:

```bash
read -rsp "PAT: " PAT; echo
AUTH="Authorization: Basic $(printf ':%s' "$PAT" | base64 | tr -d '\n')"
```

`tr -d '\n'` matters: GNU `base64` wraps its output at 76 characters, which would split a long PAT's header in two. `fetch_json` works unchanged with either `AUTH`.

Repeat for your 5-10 most recent PRs. Filter comments whose author matches the reviewer identity and whose content starts with its marker. Keep: file path, line, full text, thread status (`active` / `fixed` / `wontFix`).

## 3. Find the mechanism and the config

- **Extension?** `GET https://extmgmt.dev.azure.com/<your-org>/_apis/extensionmanagement/installedextensions?api-version=7.1-preview.1` (note the `extmgmt.` host from the official REST reference, not `dev.azure.com`; a PAT needs scope Extensions (Read)) — look for review-related publishers. Some extensions keep their rule store in extension data (`_apis/ExtensionManagement/InstalledExtensions/<publisher>/<ext>/Data/...`) — read it: the configured prompt often differs from what the bot actually posts, and cited rule IDs may not exist. The data path is documented without a host: try `extmgmt.dev.azure.com` and trust it only once `fetch_json` gets a `200` with JSON.
- **Pipeline task?** grep your repo's pipeline YAML for review tasks; note the trigger (per push?).
- **Branch policies:** `GET $ORG/<project>/_apis/policy/configurations?api-version=7.0` — find what actually blocks: comment-resolution policy, build validation, or a vote. This determines how threads must be resolved.

## 4. Categorize

Extract and count first with `scripts/tally_review_threads.py` from a clone of the adversarial-pre-pr repository (Python 3.10+, standard library only, no network; it is not part of the installed skill folder):

```bash
python scripts/tally_review_threads.py pr-*-threads.json \
  --author-contains "Build Service" --marker "[AI PR Review]" > bot-comments.csv
```

It writes one CSV row per reviewer comment (`pr, file, line, status, text, is_generated`) to stdout and a summary by status and by file to stderr. `is_generated` flags `*.Designer.cs`, `*ModelSnapshot.cs` and `*-proxy.ts` by default; pass `--generated '<glob>'` (repeatable) to use your own patterns instead. Those rows feed the "auto-generated file" class in step 5. A file that is not JSON (the HTTP 203 sign-in page) or not a threads response stops it with exit code 2 before any row is written.

Bucket every comment by MECHANISM (what code pattern triggered it), not by wording. Typical buckets: input validation, null-safety, error handling, ORM/transactions, signature drift between tests and production, test asserts, language modifiers, framework-specific (UI), security. Count per bucket; sort your checklist by count.

## 5. Separate provable false positives

A false positive qualifies ONLY with proof: the compiler accepts the flagged syntax, the file is auto-generated, the cited rule doesn't exist in the store, or the bot contradicts itself between runs. Write the proof next to each class — that text becomes your honest thread-resolution reply.

## 6. Record operational behavior

- Does it dedupe across runs? (Many don't — every push re-posts. Batch your pushes.)
- Does it comment on generated files even when its own prompt excludes them?
- Does it vote, or block only via comment resolution?

Fold all of this into your copy of the skill.
