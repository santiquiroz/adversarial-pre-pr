#!/usr/bin/env python3
import argparse
import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path

CSV_FIELDS = ("pr", "file", "line", "status", "text", "is_generated")
DEFAULT_GENERATED = ("*.Designer.cs", "*ModelSnapshot.cs", "*-proxy.ts")
PR_FILE_NAME = re.compile(r"pr-(\d+)-threads", re.IGNORECASE)
NO_FILE = "(no file)"
INPUT_ERROR = 2


class InputError(Exception):
    pass


@dataclass(frozen=True)
class Filters:
    author_contains: str
    marker: str
    generated: tuple[str, ...]


@dataclass(frozen=True)
class Finding:
    pr: str
    file: str
    line: str
    status: str
    text: str
    is_generated: bool


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Extract an AI reviewer's comments from Azure DevOps PR thread dumps into CSV (stdout) and a summary (stderr)."
    )
    parser.add_argument("files", nargs="+", type=Path, help="pr-<id>-threads.json files from the threads REST API")
    parser.add_argument("--author-contains", default="", help="case-insensitive substring of the author's display or unique name")
    parser.add_argument("--marker", default="", help="prefix the reviewer puts on every comment, e.g. '[AI PR Review]'")
    parser.add_argument(
        "--generated",
        action="append",
        metavar="GLOB",
        help=f"file-name glob that marks generated files (repeatable; default: {' '.join(DEFAULT_GENERATED)})",
    )
    return parser.parse_args(argv)


def pr_id_from_path(path):
    match = PR_FILE_NAME.search(path.name)
    return match.group(1) if match else path.stem


def read_payload(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except OSError as error:
        raise InputError(f"{path}: cannot read ({error.strerror})") from error
    except ValueError as error:
        # An expired or rejected az session makes Azure DevOps answer 203 with its HTML sign-in page.
        raise InputError(f"{path}: not JSON (an HTML sign-in page means HTTP 203: re-authenticate and fetch again)") from error


def load_threads(path):
    payload = read_payload(path)
    threads = payload.get("value") if isinstance(payload, dict) else None
    if not isinstance(threads, list):
        raise InputError(f"{path}: JSON but not an Azure DevOps threads response (no 'value' list)")
    return threads


def as_dict(value):
    return value if isinstance(value, dict) else {}


def as_list(value):
    return value if isinstance(value, list) else []


def as_text(value):
    return value if isinstance(value, str) else ""


def is_live(item):
    return isinstance(item, dict) and not item.get("isDeleted", False)


def author_matches(comment, needle):
    if not needle:
        return True
    author = as_dict(comment.get("author"))
    names = f"{as_text(author.get('displayName'))} {as_text(author.get('uniqueName'))}".lower()
    return needle.lower() in names


def is_reviewer_comment(comment, filters):
    if not is_live(comment) or comment.get("commentType") == "system":
        return False
    content = as_text(comment.get("content")).lstrip()
    return content.startswith(filters.marker) and author_matches(comment, filters.author_contains)


def thread_line(context):
    position = as_dict(context.get("rightFileStart") or context.get("leftFileStart"))
    line = position.get("line")
    return "" if line is None else str(line)


def is_generated(file_path, patterns):
    name = file_path.rsplit("/", 1)[-1]
    return bool(name) and any(fnmatchcase(name, pattern) for pattern in patterns)


def thread_findings(pr, thread, filters):
    context = as_dict(thread.get("threadContext"))
    file_path = as_text(context.get("filePath"))
    return [
        Finding(
            pr=pr,
            file=file_path,
            line=thread_line(context),
            status=as_text(thread.get("status")) or "unknown",
            text=as_text(comment.get("content")).strip(),
            is_generated=is_generated(file_path, filters.generated),
        )
        for comment in as_list(thread.get("comments"))
        if is_reviewer_comment(comment, filters)
    ]


def file_findings(path, filters):
    pr = pr_id_from_path(path)
    live_threads = (thread for thread in load_threads(path) if is_live(thread))
    return [finding for thread in live_threads for finding in thread_findings(pr, thread, filters)]


def write_csv(findings, out):
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(CSV_FIELDS)
    for finding in findings:
        writer.writerow(
            (finding.pr, finding.file, finding.line, finding.status, finding.text, str(finding.is_generated).lower())
        )


def format_counts(counter):
    ordered = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return ", ".join(f"{key}={count}" for key, count in ordered) or "-"


def summary_lines(findings):
    prs = {finding.pr for finding in findings}
    return [
        f"comments: {len(findings)} in {len(prs)} PR(s)",
        f"by status: {format_counts(Counter(finding.status for finding in findings))}",
        f"by file: {format_counts(Counter(finding.file or NO_FILE for finding in findings))}",
        f"on generated files: {sum(finding.is_generated for finding in findings)}",
    ]


def main(argv=None, out=sys.stdout, err=sys.stderr):
    args = parse_args(argv)
    filters = Filters(args.author_contains, args.marker, tuple(args.generated or DEFAULT_GENERATED))
    try:
        findings = [finding for path in args.files for finding in file_findings(path, filters)]
    except InputError as error:
        print(f"error: {error}", file=err)
        return INPUT_ERROR
    write_csv(findings, out)
    print("\n".join(summary_lines(findings)), file=err)
    return 0


def use_utf8_streams():
    # Redirected output on Windows defaults to the ANSI code page, which cannot encode many comment texts.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")


if __name__ == "__main__":
    use_utf8_streams()
    sys.exit(main())
