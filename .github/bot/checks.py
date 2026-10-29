"""Pure text checks for ICE 3 (Pair Programming). No network calls here."""
import re

ENTRY_RE = re.compile(r"^\s*[-*]\s*\*\*(?P<name>[^*]+)\*\*\s*:")


def has_conflict_markers(text):
    for line in (text or "").splitlines():
        s = line.rstrip()
        if s.startswith("<<<<<<<") or s.startswith(">>>>>>>") or s == "=======":
            return True
    return False


def readme_entries(text):
    """Team-member lines like '- **Alice Smith**: Favorite movie: ...'."""
    return [m.group("name").strip() for m in map(ENTRY_RE.match, (text or "").splitlines()) if m]


def readme_problems(text):
    if text is None:
        return ["missing_file"]
    problems = []
    if has_conflict_markers(text):
        problems.append("markers")
    section = text.split("## Team Members", 1)[-1]
    if re.search(r"^\s*-\s*TBD\s*$", section, re.M):
        problems.append("tbd")
    if len(readme_entries(section)) < 2:
        problems.append("fewer_than_two")
    return problems


def box(done):
    return "✅" if done else "⬜"


FRIENDLY = {
    "missing_file": "I couldn't find the file I expected.",
    "markers": "The file still contains conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`). Delete them.",
    "tbd": "`TBD` is still in the file. Replace it.",
    "fewer_than_two": "The Team Members section should list both partners.",
}


def explain(problems):
    return "\n".join(f"- {FRIENDLY.get(p, p)}" for p in problems)
