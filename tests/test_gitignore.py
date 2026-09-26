import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or not (ROOT / ".git").exists(), reason="needs a git checkout"
)


def is_ignored(path):
    result = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", "--no-index", path], capture_output=True)
    return result.returncode == 0


@pytest.mark.parametrize("dump", ["pr-1-threads.json", "pr-5334-threads.json", "bot-comments.csv"])
def test_private_calibration_dumps_at_the_root_are_ignored(dump):
    assert is_ignored(dump)


@pytest.mark.parametrize(
    "fixture", ["tests/fixtures/pr-101-threads.json", "tests/fixtures/expected-pr-101.csv"]
)
def test_versioned_fixtures_stay_tracked(fixture):
    assert not is_ignored(fixture)
