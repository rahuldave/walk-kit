"""Make a project's walk repository, PROJECT-walk: the repository that students fork to replay the steps.

    python3 walk_init.py --project bla --upstream owner --walk ~/Projects/bla-walk
    python3 walk_init.py ... --no-github        make it on this machine only

It holds a justfile (present, setup, pdf), a .gitignore (repo/, worktree/, walk.pdf), a README, an
AGENTS.md with a CLAUDE.md that reads it, and walk.md with only its preamble: `walk_update.py` fills it
from the class notes. The script commits the files, then asks before it creates the public repository
OWNER/PROJECT-walk on GitHub and pushes to it.
"""

import argparse
import sys
from pathlib import Path

from common import TIMEWALK, fill, run, yes

FILES = {  # a file of the walk repository: its template
    "justfile": "walk/justfile",
    ".gitignore": "walk/gitignore",
    "README.md": "walk/README.md",
    "AGENTS.md": "walk/AGENTS.md",
    "CLAUDE.md": "CLAUDE.md",
    "walk.md": "walk/walk-preamble.md",
}


def main() -> int:  # The exit code
    """Write the walk repository, commit it, and on a yes create it on GitHub."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--project", required=True, help="the project's name, as its repository is named")
    parser.add_argument("--upstream", required=True, help="the project's owner on GitHub")
    parser.add_argument("--walk", required=True, type=Path, help="the folder of the new walk repository")
    parser.add_argument("--owner", help="its owner on GitHub (default: the upstream owner)")
    parser.add_argument("--timewalk", default=TIMEWALK, help=f"timewalk to run (default: {TIMEWALK})")
    parser.add_argument("--no-github", action="store_true", help="do not create a repository on GitHub")
    args = parser.parse_args()
    walk = args.walk.expanduser().resolve()
    if walk.exists() and any(walk.iterdir()):
        print(f"walk-init: {walk} exists and is not empty. walk-update refreshes it", file=sys.stderr)
        return 2
    values = {"project": args.project, "upstream": args.upstream, "timewalk": args.timewalk}
    walk.mkdir(parents=True, exist_ok=True)
    for name, template in FILES.items():
        (walk / name).write_text(fill(template, values), encoding="utf-8")
        print(f"walk-init: wrote {walk / name}")
    run("git", "init", "--quiet", "--initial-branch=main", cwd=walk)
    run("git", "add", "-A", cwd=walk)
    run("git", "commit", "--quiet", "-m", f"The walk through {args.project}", cwd=walk)
    print(f"walk-init: {walk} is a repository with one commit")
    name = f"{args.owner or args.upstream}/{args.project}-walk"
    later = f"gh repo create {name} --public --source {walk} --remote origin --push"
    if args.no_github or not yes(f"walk-init: create the public repository github.com/{name} and push?"):
        print(f"walk-init: nothing on GitHub. To create it later: {later}")
        return 0
    run(*later.split(), cwd=walk)
    return 0


if __name__ == "__main__":
    sys.exit(main())
