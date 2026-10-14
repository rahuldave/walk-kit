"""Keep walk-kit's copy of the writing guide and its checker in step with nossaifd.

    python3 style_sync.py              say whether style/GUIDE.md and style/check.py match nossaifd's
    python3 style_sync.py --write      copy nossaifd's files over them, and note nossaifd's commit in style/README.md

nossaifd is the folder that `$NOSSAIFD` names, or `nossaifd` beside walk-kit, or else the repository on GitHub,
https://github.com/rahuldave/nossaifd, at the head of its main branch. The exit code is 1 when a file differs and
`--write` is not given.
"""

import argparse
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

from style import nossaifd

STYLE = Path(__file__).resolve().parent.parent / "style"
FILES = ("GUIDE.md", "check.py")
RAW = "https://raw.githubusercontent.com/rahuldave/nossaifd/main/"


def theirs() -> tuple[dict[str, bytes], str]:  # nossaifd's files by name, and its commit, or "main"
    """Read nossaifd's files from a clone, or from GitHub."""
    clone = nossaifd()
    if clone:
        commit = subprocess.run(["git", "-C", str(clone), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=False).stdout.strip()
        return {name: (clone / name).read_bytes() for name in FILES}, commit or "main"
    with_files = {}
    for name in FILES:
        with urllib.request.urlopen(RAW + name, timeout=30) as answer:   # a fixed https address
            with_files[name] = answer.read()
    return with_files, "main"


def main() -> int:  # The exit code
    """Compare the copies with nossaifd, and copy them over with --write."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--write", action="store_true", help="copy nossaifd's files over walk-kit's")
    args = parser.parse_args()
    found, commit = theirs()
    differ = [name for name in FILES if (STYLE / name).read_bytes() != found[name]]
    if not differ:
        print(f"style_sync: style/GUIDE.md and style/check.py match nossaifd at {commit}")
        return 0
    if not args.write:
        print(f"style_sync: {', '.join('style/' + name for name in differ)} differ from nossaifd at {commit}; run with --write to copy them")
        return 1
    for name in differ:
        (STYLE / name).write_bytes(found[name])
    readme = STYLE / "README.md"
    text = readme.read_text(encoding="utf-8")
    readme.write_text(re.sub(r"at its\s+commit \w+\.", f"at its\ncommit {commit}.", text, count=1), encoding="utf-8")
    print(f"style_sync: copied {', '.join(differ)} from nossaifd at {commit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
