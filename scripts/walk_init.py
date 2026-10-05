"""Make the walk kit of a project: a new repository that students fork, to replay the project's steps.

    python3 walk_init.py --project bla --upstream owner --kit ~/Projects/bla-walk
    python3 walk_init.py ... --no-github        make the kit on this machine only

The kit holds a justfile (present, setup, pdf), a .gitignore (repo/, worktree/, walk.pdf), a README, an
AGENTS.md with a CLAUDE.md that reads it, and walk.md with only its preamble: `walk_update.py` fills it
from the class notes. The script commits the files, then asks before it creates the public repository
OWNER/PROJECT-walk on GitHub and pushes to it.
"""

import argparse
import sys
from pathlib import Path

from common import TIMEWALK, fill, run, yes

FILES = {  # the kit's file: its template
    "justfile": "walk/justfile",
    ".gitignore": "walk/gitignore",
    "README.md": "walk/README.md",
    "AGENTS.md": "walk/AGENTS.md",
    "CLAUDE.md": "CLAUDE.md",
    "walk.md": "walk/walk-preamble.md",
}


def main() -> int:  # The exit code
    """Write the kit, commit it, and on a yes create its repository on GitHub."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--project", required=True, help="the project's name, as its repository is named")
    parser.add_argument("--upstream", required=True, help="the project's owner on GitHub")
    parser.add_argument("--kit", required=True, type=Path, help="the folder of the new kit")
    parser.add_argument("--owner", help="the kit's owner on GitHub (default: the upstream owner)")
    parser.add_argument("--timewalk", default=TIMEWALK, help=f"timewalk to run (default: {TIMEWALK})")
    parser.add_argument("--no-github", action="store_true", help="do not create a repository on GitHub")
    args = parser.parse_args()
    kit = args.kit.expanduser().resolve()
    if kit.exists() and any(kit.iterdir()):
        print(f"walk-init: {kit} exists and is not empty. walk-update refreshes a kit", file=sys.stderr)
        return 2
    values = {"project": args.project, "upstream": args.upstream, "timewalk": args.timewalk}
    kit.mkdir(parents=True, exist_ok=True)
    for name, template in FILES.items():
        (kit / name).write_text(fill(template, values), encoding="utf-8")
        print(f"walk-init: wrote {kit / name}")
    run("git", "init", "--quiet", "--initial-branch=main", cwd=kit)
    run("git", "add", "-A", cwd=kit)
    run("git", "commit", "--quiet", "-m", f"The walk kit for {args.project}", cwd=kit)
    print(f"walk-init: {kit} is a repository with one commit")
    repo = f"{args.owner or args.upstream}/{args.project}-walk"
    later = f"gh repo create {repo} --public --source {kit} --remote origin --push"
    if args.no_github or not yes(f"walk-init: create the public repository github.com/{repo} and push?"):
        print(f"walk-init: nothing on GitHub. To create it later: {later}")
        return 0
    run(*later.split(), cwd=kit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
