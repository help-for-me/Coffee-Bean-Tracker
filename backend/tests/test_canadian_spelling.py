import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# American-only spellings this project has actually hit before (see
# CLAUDE.md's "Canadian English" policy) - not an exhaustive dictionary,
# just a regression guard. Deliberately narrow: Canadian English keeps
# American "-ize"/"-yze" endings and "program", so those are never here.
_BLOCKED = ["flavor", "favorite", "behavior", "neighbor", "honor", "defense", "color"]
_PATTERN = re.compile(r"\b(" + "|".join(_BLOCKED) + r")\b", re.IGNORECASE)


def _files_to_scan():
    # .md and backend .py only - Tailwind's own class names (bg-gray-500,
    # items-center) make .jsx/.js too noisy to scan this way; frontend text
    # gets reviewed by eye when it's written instead.
    for path in (REPO_ROOT / "backend").rglob("*.py"):
        if "tests" not in path.relative_to(REPO_ROOT).parts and "__pycache__" not in str(path):
            yield path
    for path in REPO_ROOT.glob("*.md"):
        yield path


def test_no_american_only_spelling_in_docs_and_backend_prose():
    violations = []
    for path in _files_to_scan():
        text = path.read_text(encoding="utf-8")
        for match in _PATTERN.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            violations.append(f"{path.relative_to(REPO_ROOT)}:{line_no}: {match.group()!r}")
    assert not violations, "American-only spelling found (project policy is Canadian English):\n" + "\n".join(
        violations
    )
