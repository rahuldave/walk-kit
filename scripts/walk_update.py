"""Refresh a project's walk repository, PROJECT-walk, from the class material, and commit on a yes.

    python3 walk_update.py --project bla --notes notes.md --walk ~/Projects/bla-walk
    python3 walk_update.py ... --slides slides         also copy the slides folder and its manifest
    python3 walk_update.py ... --pdf                   also ship bla.pdf, the walk as written
    python3 walk_update.py ... --no-commit             write and show, and do not ask to commit

walk.md is the walk's preamble, then the class notes from their first `## ` heading on, without the
private lines that `private.py` names. The script never writes walk.pdf, the student's own PDF. It never
pushes: it prints the command that does.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from common import TIMEWALK, UVX, run, walk_text, yes
from private import is_private


def main() -> int:  # The exit code
    """Write the walk repository's files, show what changed, and commit on a yes."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--project", required=True, help="the project's name")
    parser.add_argument("--notes", required=True, type=Path, help="the class notes, with the private cues")
    parser.add_argument("--walk", required=True, type=Path, help="the walk repository, PROJECT-walk")
    parser.add_argument("--slides", type=Path, help="a slides folder with slides.toml, to copy there")
    parser.add_argument("--pdf", action="store_true", help="also ship PROJECT.pdf, the walk as written")
    parser.add_argument("--timewalk", default=TIMEWALK, help=f"timewalk for the PDF (default: {TIMEWALK})")
    parser.add_argument("--message", default="The walk, from the class notes", help="the commit message")
    parser.add_argument("--no-commit", action="store_true", help="write and show the diff; do not commit")
    args = parser.parse_args()
    walk = args.walk.expanduser().resolve()
    if not (walk / ".git").exists():
        print(f"walk-update: {walk} is not a git repository. walk-init makes it", file=sys.stderr)
        return 2
    notes = args.notes.read_text(encoding="utf-8")
    (walk / "walk.md").write_text(walk_text(notes, args.project), encoding="utf-8")
    dropped = sum(is_private(line) for line in notes.split("\n"))
    print(f"walk-update: wrote walk.md, without {dropped} private lines")
    if args.slides:
        if not (args.slides / "slides.toml").exists():
            print(f"walk-update: {args.slides} has no slides.toml", file=sys.stderr)
            return 2
        if (walk / "slides").exists():
            shutil.rmtree(walk / "slides")
        shutil.copytree(args.slides, walk / "slides")
        print("walk-update: copied the slides and their manifest into slides/")
    if args.pdf:
        manifest = ["slides/slides.toml"] if (walk / "slides" / "slides.toml").exists() else []
        out = f"{args.project}.pdf"
        run(*UVX, args.timewalk, "timewalk-pdf", *manifest, "--notes", "walk.md",
            "--with-notes", "--title", args.project, "-o", out, cwd=walk)
    run("git", "add", "-A", cwd=walk)
    if subprocess.run(["git", "-C", str(walk), "diff", "--cached", "--quiet"]).returncode == 0:
        print(f"walk-update: {walk.name} has no changes")
        return 0
    run("git", "diff", "--cached", "--stat", cwd=walk)
    run("git", "diff", "--cached", cwd=walk)
    if args.no_commit or not yes(f"walk-update: commit these changes in {walk}?"):
        run("git", "reset", "--quiet", cwd=walk)
        print("walk-update: written, not committed")
        return 0
    run("git", "commit", "--quiet", "-m", args.message, cwd=walk)
    print(f"walk-update: committed. To publish it: git -C {walk} push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
