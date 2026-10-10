"""What the scripts share: where timewalk comes from, the templates, the walks of a toc.toml, and the student's notes.

timewalk is not pinned: every run fetches the newest commit on GitHub (`--refresh-package timewalk`), so a
new timewalk reaches every class at once. The environment variable TIMEWALK names another source, for
example a working copy, `TIMEWALK=~/Projects/timewalk`. The templates always name GitHub,
through `@timewalk@`, whatever TIMEWALK says when they are filled.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

from private import fenced, private_lines, public

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
# what the templates name. On walk-kit's branch walks, timewalk's branch walks, which has the walks, the tutorials and the
# saved branches. Back to "git+https://github.com/rahuldave/timewalk" when timewalk releases walks: both branches merge then
GITHUB = "git+https://github.com/rahuldave/timewalk@walks"
TIMEWALK = os.environ.get("TIMEWALK", GITHUB)  # what a run of these scripts uses
UVX = ["uvx", "--refresh-package", "timewalk", "--from"]  # then the source, then the command
NO_TOML = 3  # the exit code of `common.py manifest` under a Python without tomllib: the class justfile goes on without it


class TocError(Exception):
    """A toc.toml that the scripts cannot use, with the reason."""


class NoToml(TocError):
    """A Python before 3.11, which has no tomllib to read toc.toml."""


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
) -> tuple[str, int]:  # The notes for students: the walk's preamble, then the steps without the private lines. And the number of lines dropped from the steps
    """Make the students' notes from the class notes."""
    # The private lines go first, from the whole file. Then the class's preamble goes: all before the first `## ` heading
    # outside fenced code, as timewalk reads the notes. So a `## ` in a fence of the preamble cannot let a private line through
    lines, drop = notes.split("\n"), set(private_lines(notes))
    code = fenced(lines)
    start = next((at for at, line in enumerate(lines) if at not in code and at not in drop and re.match(r"^##\s", line)), len(lines))
    return fill("walk/walk-preamble.md", {"project": project}) + public(notes, start), len([at for at in drop if at >= start])


def toc_walks(
    toc: Path,  # A table of contents, toc.toml, of a class with several walks
) -> list[dict[str, str | None]]:  # Each walk in order: its id, and its folder, notes and manifest from the folder of toc.toml, or None
    """Read the walks of a table of contents: where the folder, the notes and the slides of each one are.

    Raises `TocError` for a toc.toml that cannot be read, or that names a path that is absolute, has a `..`, or leads out
    of the folder of toc.toml. `NoToml` is the TocError of a Python before 3.11."""
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10 has none
        raise NoToml("a class with toc.toml needs Python 3.11 or later, which reads TOML") from None
    try:
        table = tomllib.loads(toc.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise TocError(f"cannot read {toc}: {error}") from None
    found = []
    for walk in table.get("walk", []):
        folder = walk.get("folder")
        paths = {"folder": folder,
                 "notes": walk.get("notes") or (f"{folder}/notes.md" if folder else None),
                 "slides": walk.get("slides") or (f"{folder}/slides/slides.toml" if folder else None)}
        for key, path in paths.items():
            if path is None:
                continue
            if not isinstance(path, str) or Path(path).is_absolute() or ".." in Path(path).parts or not Path(path).parts:
                raise TocError(f"in {toc}, the {key} of walk {walk.get('id')} is {path!r}. Give a path inside the class folder, "
                               "from the folder of toc.toml, with no `..`")
            if not (toc.parent / path).resolve().is_relative_to(toc.parent.resolve()):
                raise TocError(f"in {toc}, the {key} of walk {walk.get('id')} leads outside the class folder: {path}")
        found.append({"id": walk.get("id"), **paths})
    return found


def manifest_of(
    toc: Path,  # A table of contents, toc.toml
    wanted: str | None = None,  # The id of a walk; None for the first walk
) -> Path:  # The slides manifest of that walk. The script stops with a message if it has none
    """Find the slides manifest of a walk of a table of contents."""
    walks = toc_walks(toc)
    wanted = wanted or (walks[0]["id"] if walks else None)
    walk = next((found for found in walks if found["id"] == wanted), None)
    if walk is None:
        raise TocError(f"{toc.name} has no walk {wanted}")
    if walk["slides"] is None or not (toc.parent / walk["slides"]).is_file():
        where = f" {walk['slides']}" if walk["slides"] else ""
        raise TocError(f"walk {wanted} has no slides manifest{where}, so it has no PDF. Its notes are for the step browser: just present")
    return toc.parent / walk["slides"]


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
    if not sys.stdin.isatty():
        return False
    return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")


if __name__ == "__main__":
    # python3 common.py manifest toc.toml [ID]: print the slides manifest of a walk, or say that it has none. The exit code
    # is NO_TOML, with nothing said, under a Python that cannot read toc.toml: timewalk then says what is wrong, if anything
    if sys.argv[1:2] != ["manifest"] or len(sys.argv) not in (3, 4):
        sys.exit("usage: python3 common.py manifest toc.toml [ID]")
    try:
        print(manifest_of(Path(sys.argv[2]), sys.argv[3] if len(sys.argv) == 4 else None))
    except NoToml:
        sys.exit(NO_TOML)
    except TocError as error:
        sys.exit(f"walk: {error}")
