"""Check the prose of a class against the writing guide, style/GUIDE.md, with the checker style/check.py.

    python3 style.py                  check the class in this folder
    python3 style.py --class DIR      check the class in DIR
    python3 style.py -v               also show the soft notes, for a person to judge
    python3 style.py PAGE.md ...      check these files, such as the pages that render.py writes

The script checks the prose of the class, and nothing else of its folder: README.md, AGENTS.md and CLAUDE.md, the
notes of every walk, and the Markdown files that the slides manifest of each walk names. The walks are those of
toc.toml, or else notes.md with slides/slides.toml. This docstring is the one place that says which files are checked.

The checker reads a copy of each file in which the forms that the notes own are blank lines, so each line keeps its
number. Those forms are a command line, such as `$ just setup` or `runs$ uv run train`, and a line `time: m:ss`. The
words of each item under `files:` are checked as prose: the pages show them under What changed. check.py itself is a
copy from nossaifd, and stays as it is.
"""

import argparse
import importlib.util
import re
import sys
import tempfile
from pathlib import Path

from common import TocError, toc_walks

CHECKER = Path(__file__).resolve().parent.parent / "style" / "check.py"
COMMAND = re.compile(r"^\s*[A-Za-z0-9_]*\$(\s|$)")  # $ cmd, runs$ cmd, main$ cmd
TIME = re.compile(r"^\s*time:\s*\d")


def checker() -> object:  # The module style/check.py
    """Load the checker as a module, as it is."""
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
    """Find the prose of a class: its README, AGENTS.md and CLAUDE.md, the notes and intro of every walk, and the slides."""
    files = [folder / name for name in ("README.md", "AGENTS.md", "CLAUDE.md")]
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
    parser.add_argument("files", nargs="*", type=Path, help="files to check in place of the class's prose, such as rendered pages")
    args = parser.parse_args()
    folder = args.folder.expanduser().resolve()
    files, problems, warnings = ([path.resolve() for path in args.files], [], []) if args.files else prose_files(folder)
    for problem in problems + warnings:
        print(f"style: {problem}", file=sys.stderr)
    if not files:
        print(f"style: {folder} has no prose to check: no README.md, AGENTS.md, notes or slides", file=sys.stderr)
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
    return 1 if failed or problems else 0


if __name__ == "__main__":
    sys.exit(main())
