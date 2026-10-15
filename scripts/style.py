"""Check the prose of a class against the writing guide, style/GUIDE.md: its form with style/check.py, then its language with a model.

    python3 style.py                  check the class in this folder
    python3 style.py --class DIR      check the class in DIR
    python3 style.py -v               also show the soft notes, for a person to judge
    python3 style.py PAGE.md ...      check these files, such as the pages that render.py writes
    python3 style.py --repo DIR       let the review read the project in DIR, at the commit of each section of the notes
    python3 style.py --all            review each file whole, not only the text changed since the last commit

style/check.py checks the mechanical rules of the guide: the length of a sentence, a colon, a contraction, a dash. It
is not a review of the writing. When the form passes, review.py asks a model to review the text that changed since the
last commit, for a reader of 12, with the reviewer's prompt in review/writing.md. A finding fails the check too. With
--all, the model reviews each file whole: once, when a class takes up the review, so that the text written before it is
reviewed too, and after big edits. The limit of 3 reviews of a file between two commits holds with --all too.

The script checks the prose that people outside the class's authors read, and nothing else of its folder: README.md,
the notes and intro of every walk, and the Markdown files that the slides manifest of each walk names. The walks are
those of toc.toml, or else notes.md with slides/slides.toml. AGENTS.md and CLAUDE.md are for agents, and are not
checked. Rendered pages are checked when they are given as files. This docstring is the one place that says which
files are checked.

The checker reads a copy of each file in which the forms that the notes own are blank lines, so each line keeps its
number. Those forms are a command line, such as `$ just setup` or `runs$ uv run train`, and a line `time: m:ss`. The
words of each item under `files:` are checked as prose: the pages show them under What changed.

The checker is nossaifd's own `check.py` when a clone of nossaifd is on this machine: the folder that `$NOSSAIFD` names,
or `nossaifd` beside walk-kit. Otherwise it is the copy in `style/check.py`, which `style_sync.py` keeps in step with
nossaifd. A copy that differs from the clone is named, so that it does not fall behind unseen.
"""

import argparse
import importlib.util
import re
import sys
import tempfile
from pathlib import Path

from common import TocError, toc_walks

COPY = Path(__file__).resolve().parent.parent / "style" / "check.py"


def nossaifd() -> Path | None:  # A clone of nossaifd on this machine, or None
    """Find nossaifd: the folder that $NOSSAIFD names, or nossaifd beside walk-kit."""
    import os

    for folder in (os.environ.get("NOSSAIFD"), COPY.parent.parent.parent / "nossaifd"):
        if folder and (Path(folder) / "check.py").is_file():
            return Path(folder)
    return None


CLONE = nossaifd()
CHECKER = CLONE / "check.py" if CLONE else COPY
COMMAND = re.compile(r"^\s*[A-Za-z0-9_]*\$(\s|$)")  # $ cmd, runs$ cmd, main$ cmd
TIME = re.compile(r"^\s*time:\s*\d")


def checker() -> object:  # The module check.py, nossaifd's own or the copy
    """Load the checker as a module, as it is, and say when the copy differs from nossaifd's."""
    if CLONE and COPY.read_bytes() != CHECKER.read_bytes():
        print(f"style: walk-kit's style/check.py differs from nossaifd's, in {CLONE}; this check uses nossaifd's. "
              "Run scripts/style_sync.py --write to copy it", file=sys.stderr)
    spec = importlib.util.spec_from_file_location("nossaifd_check", CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def manifest_files(
    manifest: Path,  # A slides manifest, slides.toml
) -> list[Path]:  # The Markdown files that it names
    """Read the Markdown files of a slides manifest: its deck, its slides and its documents."""
    import tomllib  # the caller has checked that this Python has it

    data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    entries = [data.get("deck", "")]
    for value in data.get("slides", {}).values():
        entries += value if isinstance(value, list) else []
    entries += list(data.get("docs", {}).values())
    names = {entry.partition("#")[0].strip() for entry in entries if isinstance(entry, str)}
    return [manifest.parent / name for name in sorted(names) if name.endswith(".md")]


def prose_files(
    folder: Path,  # The class folder
) -> tuple[list[Path], list[str], list[str]]:  # The files to check, the errors, and the notes for the user
    """Find the prose of a class that its readers see: its README, the notes and intro of every walk, and the slides."""
    files = [folder / "README.md"]
    notes, manifests, problems, warnings = [], [], [], []   # notes: (what it is, its path)
    toc = folder / "toc.toml"
    if toc.is_file():
        try:
            for walk in toc_walks(toc):
                notes += [(key, folder / walk[key]) for key in ("notes", "intro") if walk[key]]
                manifests += [folder / walk["slides"]] if walk["slides"] else []
        except TocError as error:
            problems.append(str(error))
    else:
        notes, manifests = [("notes", folder / "notes.md")], [folder / "slides" / "slides.toml"]
    for key, path in notes:
        if path.is_file():
            files.append(path)
        else:
            problems.append(f"the {key} {path.relative_to(folder)} " + ("are missing" if key == "notes" else "is missing"))
    root = folder.resolve()
    for manifest in (found for found in manifests if found.is_file()):
        try:
            for slide in manifest_files(manifest):
                if slide.resolve().is_relative_to(root):
                    files.append(slide)
                else:
                    problems.append(f"{manifest.relative_to(folder)} names {slide.name}, which is outside the class folder, {slide.resolve()}")
        except ModuleNotFoundError:
            warnings.append(f"{manifest.relative_to(folder)} is TOML, which Python 3.11 or later reads, so its slides are not checked")
        except (OSError, UnicodeDecodeError, ValueError) as error:
            problems.append(f"cannot read {manifest.relative_to(folder)}: {error}")
    seen, found = set(), []
    for path in files:
        if path.is_file() and path.resolve() not in seen:
            seen.add(path.resolve())
            found.append(path)
    return found, problems, warnings


def blank(
    text: str,  # A Markdown file of the class
) -> str:  # The same file with the forms that the notes own as blank lines, so every line keeps its number
    """Blank the command lines and the time lines, which have their own form."""
    return "\n".join("" if COMMAND.match(line) or TIME.match(line) else line for line in text.split("\n"))


def main() -> int:  # The exit code: 1 if a file has a hard problem
    """Check the prose of a class, and say each problem with its file and line."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--class", dest="folder", type=Path, default=Path("."), help="the class folder (default: this folder)")
    parser.add_argument("-v", action="store_true", help="also show the soft notes, for a person to judge")
    parser.add_argument("--repo", type=Path, help="the project, which the review may read")
    parser.add_argument("--all", action="store_true", help="review each file whole, not only its change since the last commit")
    parser.add_argument("files", nargs="*", type=Path, help="files to check in place of the class's prose, such as rendered pages")
    args = parser.parse_args()
    folder = args.folder.expanduser().resolve()
    files, problems, warnings = ([path.resolve() for path in args.files], [], []) if args.files else prose_files(folder)
    for problem in problems + warnings:
        print(f"style: {problem}", file=sys.stderr)
    if not files:
        print(f"style: {folder} has no prose to check: no README.md, notes or slides", file=sys.stderr)
        return 2
    check, failed = checker().check, False
    with tempfile.TemporaryDirectory() as scratch:
        copy = Path(scratch) / "page.md"
        for path in files:
            name = path.relative_to(folder) if path.is_relative_to(folder) else path
            try:
                copy.write_text(blank(path.read_text(encoding="utf-8")), encoding="utf-8")
            except (OSError, UnicodeDecodeError) as error:
                print(f"style: cannot read {name}: {error}", file=sys.stderr)
                failed = True
                continue
            hard, soft = check(copy)
            print(f"{name}: {len(hard)} hard, {len(soft)} soft")
            for problem in hard:
                print("  HARD " + problem)
            for note in soft if args.v else []:
                print("  soft " + note)
            failed = failed or bool(hard)
    if failed or problems:
        return 1
    from review import run  # here: review.py imports this module

    count, broke = run(files, args.all, folder, args.repo.expanduser().resolve() if args.repo else None)
    for path in broke:
        print(f"style: the review of {path} failed", file=sys.stderr)
    return 1 if count or broke else 0


if __name__ == "__main__":
    sys.exit(main())
