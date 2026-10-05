"""What the scripts share: the version of timewalk, the templates, and the student's notes.

The version of timewalk is written here and nowhere else. Every template that names timewalk gets it
from here, through `@timewalk@`.
"""

import subprocess
from pathlib import Path

from private import public

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
TIMEWALK = "git+https://github.com/rahuldave/timewalk@v1.0.1"


def fill(
    template: str,  # A path under templates/, for example "walk/justfile"
    values: dict[str, str],  # What replaces each @key@
) -> str:  # The template with every @key@ replaced
    """Read a template and put the project's values into it."""
    text = (TEMPLATES / template).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace(f"@{key}@", value)
    return text


def walk_text(
    notes: str,  # The class notes, with the presenter's private cues
    project: str,  # The project's name, for the title
) -> str:  # The notes for students: the kit's preamble, then the steps without the private lines
    """Make the students' notes from the class notes."""
    start = notes.find("\n## ")
    body = notes[start + 1 :] if start >= 0 else ""
    return fill("walk/walk-preamble.md", {"project": project}) + public(body)


def run(
    *args: str,  # A command and its arguments
    cwd: Path,  # The folder to run it in
) -> None:
    """Run a command, and stop the script if it fails."""
    subprocess.run(args, cwd=cwd, check=True)


def yes(
    question: str,  # What to ask, ending in a question mark
) -> bool:  # True only for a typed yes, at a terminal
    """Ask a yes-or-no question. Without a terminal to ask at, the answer is no."""
    import sys

    if not sys.stdin.isatty():
        return False
    return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")
