import csv
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
SCRIPT = ROOT / "scripts" / "tally_review_threads.py"
sys.path.insert(0, str(SCRIPT.parent))

import tally_review_threads as tally  # noqa: E402

BOT = "build service"
MARKER = "[AI PR Review]"


def run_main(*args):
    out, err = io.StringIO(), io.StringIO()
    code = tally.main([str(a) for a in args], out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def parse_csv(text):
    return list(csv.DictReader(io.StringIO(text)))


def test_sample_produces_expected_csv():
    code, out, _ = run_main(FIXTURES / "pr-101-threads.json", "--author-contains", BOT, "--marker", MARKER)

    expected = (FIXTURES / "expected-pr-101.csv").read_text(encoding="utf-8")
    assert code == 0
    assert out == expected


def test_skips_human_replies_deleted_and_system_comments():
    _, out, _ = run_main(FIXTURES / "pr-101-threads.json", "--author-contains", BOT, "--marker", MARKER)

    texts = " ".join(row["text"] for row in parse_csv(out))
    assert "Good catch" not in texts
    assert "must be skipped" not in texts


def test_marker_only_keeps_every_author_using_it():
    _, out, _ = run_main(FIXTURES / "pr-101-threads.json", "--marker", MARKER)

    rows = parse_csv(out)
    assert len(rows) == 5
    assert rows[-1]["text"] == "[AI PR Review] Same marker, different author."


def test_author_filter_is_case_insensitive_and_matches_unique_name():
    _, by_display, _ = run_main(FIXTURES / "pr-101-threads.json", "--author-contains", "SAMPLE BUILD")
    _, by_unique, _ = run_main(FIXTURES / "pr-101-threads.json", "--author-contains", "build-service-0001")

    assert len(parse_csv(by_display)) == 4
    assert parse_csv(by_display) == parse_csv(by_unique)


def test_takes_line_from_left_side_when_right_is_missing():
    _, out, _ = run_main(FIXTURES / "pr-101-threads.json", "--marker", MARKER)

    snapshot = next(row for row in parse_csv(out) if row["file"].endswith("ModelSnapshot.cs"))
    assert snapshot["line"] == "120"


def test_marks_default_generated_patterns():
    _, out, _ = run_main(FIXTURES / "pr-102-threads.json", "--marker", MARKER)

    flags = {row["file"]: row["is_generated"] for row in parse_csv(out)}
    assert flags == {"/src/Web/app/api/orders-proxy.ts": "true", "/src/Api/OrdersController.cs": "false"}


def test_custom_generated_patterns_replace_the_defaults():
    _, out, _ = run_main(FIXTURES / "pr-102-threads.json", "--marker", MARKER, "--generated", "*Controller.cs")

    flags = {row["file"]: row["is_generated"] for row in parse_csv(out)}
    assert flags == {"/src/Web/app/api/orders-proxy.ts": "false", "/src/Api/OrdersController.cs": "true"}


def test_summary_counts_across_several_prs():
    _, _, err = run_main(
        FIXTURES / "pr-101-threads.json",
        FIXTURES / "pr-102-threads.json",
        "--author-contains",
        BOT,
        "--marker",
        MARKER,
    )

    assert "comments: 6 in 2 PR(s)" in err
    assert "by status: active=4, fixed=1, wontFix=1" in err
    assert "/src/Api/OrdersController.cs=2" in err
    assert "(no file)=1" in err
    assert "on generated files: 2" in err


def test_pr_id_comes_from_the_file_name_or_falls_back_to_the_stem(tmp_path):
    renamed = tmp_path / "sprint-9.json"
    renamed.write_bytes((FIXTURES / "pr-102-threads.json").read_bytes())

    _, out, _ = run_main(FIXTURES / "pr-102-threads.json", renamed, "--marker", MARKER)

    assert {row["pr"] for row in parse_csv(out)} == {"102", "sprint-9"}


def test_html_input_is_rejected_as_not_json():
    code, out, err = run_main(FIXTURES / "html-signin-threads.json")

    assert code != 0
    assert out == ""
    assert "not JSON" in err
    assert "html-signin-threads.json" in err


def test_json_without_threads_list_is_rejected(tmp_path):
    wrong = tmp_path / "pr-7-threads.json"
    wrong.write_text('{"message": "TF401019: repository not found"}', encoding="utf-8")

    code, out, err = run_main(wrong)

    assert code != 0
    assert out == ""
    assert "not an Azure DevOps threads response" in err


def test_missing_file_is_reported(tmp_path):
    code, _, err = run_main(tmp_path / "pr-404-threads.json")

    assert code != 0
    assert "pr-404-threads.json" in err


def test_accepts_utf8_bom(tmp_path):
    with_bom = tmp_path / "pr-55-threads.json"
    with_bom.write_bytes(b"\xef\xbb\xbf" + (FIXTURES / "pr-102-threads.json").read_bytes())

    code, out, _ = run_main(with_bom, "--marker", MARKER)

    assert code == 0
    assert len(parse_csv(out)) == 2


@pytest.mark.parametrize(
    ("fixture", "expected_code"),
    [("pr-101-threads.json", 0), ("html-signin-threads.json", 2)],
)
def test_command_line_exit_codes(fixture, expected_code):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURES / fixture), "--marker", MARKER],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == expected_code
    if expected_code:
        assert "not JSON" in result.stderr


def test_binary_input_is_rejected_as_not_json(tmp_path):
    binary = tmp_path / "pr-8-threads.json"
    binary.write_bytes(b"\x1f\x8b\x08\x00\xff\xfe\x00")

    code, out, err = run_main(binary)

    assert code != 0
    assert out == ""
    assert "not JSON" in err


def test_command_line_writes_utf8_whatever_the_console_encoding(tmp_path):
    unicode_dump = tmp_path / "pr-9-threads.json"
    unicode_dump.write_text(
        '{"value": [{"status": "active", "comments": [{"content": "[AI PR Review] validación → ✅"}]}]}',
        encoding="utf-8",
    )
    env = {key: value for key, value in os.environ.items() if key not in ("PYTHONIOENCODING", "PYTHONUTF8")}

    result = subprocess.run([sys.executable, str(SCRIPT), str(unicode_dump)], capture_output=True, env=env)

    assert result.returncode == 0, result.stderr
    assert "validación → ✅" in result.stdout.decode("utf-8")
