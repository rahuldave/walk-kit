"""Make the students' PDF in the class material: the slides, with the notes of each step, no private cues.

    python3 student_pdf.py --project bla --notes notes.md --out build/bla-student.pdf
    python3 student_pdf.py ... --slides slides         put the slides before the notes of each step

The notes are the ones the kit gets from `walk_update.py`, so the PDF is what a student sees. They are
written beside the PDF, as PROJECT-walk.md, because timewalk-pdf reads a file. Keep the output folder out of
git: the PDF is made again whenever the notes change.
"""

import argparse
import sys
from pathlib import Path

from common import TIMEWALK, run, walk_text


def main() -> int:  # The exit code
    """Write the students' notes and make their PDF."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--project", required=True, help="the project's name, for the title")
    parser.add_argument("--notes", required=True, type=Path, help="the class notes, with the private cues")
    parser.add_argument("--out", required=True, type=Path, help="the PDF to write")
    parser.add_argument("--slides", type=Path, help="a slides folder with slides.toml")
    parser.add_argument("--timewalk", default=TIMEWALK, help=f"timewalk to run (default: {TIMEWALK})")
    args = parser.parse_args()
    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    notes = out.with_name(f"{args.project}-walk.md")
    notes.write_text(walk_text(args.notes.read_text(encoding="utf-8"), args.project), encoding="utf-8")
    manifest = [str((args.slides / "slides.toml").resolve())] if args.slides else []
    run("uvx", "--from", args.timewalk, "timewalk-pdf", *manifest, "--notes", str(notes), "--with-notes",
        "--title", args.project, "-o", str(out), cwd=Path.cwd())
    return 0


if __name__ == "__main__":
    sys.exit(main())
