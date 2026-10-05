"""Make the class material for a project: a private repository with notes, slides and the recipes.

    python3 class_init.py --project bla --upstream owner --repo ~/Projects/bla --dir ~/Projects/bla-class
    python3 class_init.py ... --no-github        make it on this machine only

notes.md gets one section for each step tag of the project, `## step-NN Title`, with the first line of
the tag's note as the title and the rest of the note as a start for the prose. The justfile has setup,
present, handout, student-pdf, walk-init and walk-update. It finds the project and the walk
repository beside the class folder, so a clone on another machine finds them too, after `just setup`. The script commits the files, then asks before it
creates the private repository OWNER/PROJECT-class on GitHub and pushes to it.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from common import TIMEWALK, fill, run, yes

FILES = {  # the class repository's file: its template
    "justfile": "class/justfile",
    ".gitignore": "class/gitignore",
    "README.md": "class/README.md",
    "AGENTS.md": "class/AGENTS.md",
    "CLAUDE.md": "CLAUDE.md",
    "slides/slides.toml": "class/slides.toml",
}


def steps(
    repo: Path,  # The project's repository
) -> list[tuple[str, str, str]]:  # Each step tag, the first line of its note, and the rest of the note
    """Read the step tags of the project, in order, with their notes."""
    names = subprocess.run(["git", "-C", str(repo), "tag", "-l", "step-*", "--sort=version:refname"],
                           check=True, capture_output=True, text=True).stdout.split()
    found = []
    for name in names:
        note = subprocess.run(["git", "-C", str(repo), "tag", "-l", "--format=%(contents)", name],
                              check=True, capture_output=True, text=True).stdout.strip()
        title, _, rest = note.partition("\n")
        found.append((name, title.strip(), rest.strip()))
    return found


def default(
    path: Path,  # The project or the walk repository
    folder: Path,  # The class folder
    name: str,  # The folder's name when it sits beside the class folder
) -> str:  # A just expression: the folder beside this justfile, or else the path as written
    """Say where the justfile finds a folder, so that a clone on another machine finds it too."""
    if path == folder.parent / name:
        return f'parent_directory(justfile_directory()) / "{name}"'
    return f'"{path}"'


def notes_text(
    project: str,  # The project's name
    repo: Path,  # The project's repository
) -> str:  # notes.md: the preamble, then one section for each step
    """Start the class notes from the project's step tags."""
    text = fill("class/notes-preamble.md", {"project": project})
    for name, title, rest in steps(repo):
        text += f"## {name} {title}\n\n{rest}\n\n" if rest else f"## {name} {title}\n\n"
    return text


def main() -> int:  # The exit code
    """Write the class material, commit it, and on a yes create its private repository on GitHub."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--project", required=True, help="the project's name, as its repository is named")
    parser.add_argument("--upstream", required=True, help="the project's owner on GitHub")
    parser.add_argument("--repo", required=True, type=Path, help="the project's repository, with step tags")
    parser.add_argument("--dir", required=True, type=Path, help="the folder of the new class material")
    parser.add_argument("--walk", type=Path, help="the walk repository (default: PROJECT-walk beside --dir)")
    parser.add_argument("--timewalk", default=TIMEWALK, help=f"timewalk to run (default: {TIMEWALK})")
    parser.add_argument("--no-github", action="store_true", help="do not create a repository on GitHub")
    args = parser.parse_args()
    folder = args.dir.expanduser().resolve()
    repo = args.repo.expanduser().resolve()
    walk = (args.walk or folder.parent / f"{args.project}-walk").expanduser().resolve()
    if folder.exists() and any(folder.iterdir()):
        print(f"class-init: {folder} exists and is not empty", file=sys.stderr)
        return 2
    if not (repo / ".git").exists():
        print(f"class-init: {repo} is not a git repository", file=sys.stderr)
        return 2
    values = {"project": args.project, "upstream": args.upstream, "timewalk": args.timewalk,
              "repo_default": default(repo, folder, args.project),
              "walk_default": default(walk, folder, f"{args.project}-walk")}
    if repo.parent != folder.parent:
        print(f"class-init: {repo} is not beside {folder}; the justfile names it, so a clone elsewhere "
              "needs PROJECT_DIR")
    (folder / "slides").mkdir(parents=True, exist_ok=True)
    for name, template in FILES.items():
        (folder / name).write_text(fill(template, values), encoding="utf-8")
    (folder / "notes.md").write_text(notes_text(args.project, repo), encoding="utf-8")
    print(f"class-init: wrote {folder}, with {len(steps(repo))} steps in notes.md")
    run("git", "init", "--quiet", "--initial-branch=main", cwd=folder)
    run("git", "add", "-A", cwd=folder)
    run("git", "commit", "--quiet", "-m", f"The class material for {args.project}", cwd=folder)
    name = f"{args.upstream}/{args.project}-class"
    later = f"gh repo create {name} --private --source {folder} --remote origin --push"
    if args.no_github or not yes(f"class-init: create the private repository github.com/{name} and push?"):
        print(f"class-init: nothing on GitHub. To create it later: {later}")
        return 0
    run(*later.split(), cwd=folder)
    return 0


if __name__ == "__main__":
    sys.exit(main())
