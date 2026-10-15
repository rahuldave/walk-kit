"""Review the prose that changed against the writing guide, with a model, and fail on any finding.

    python3 review.py                        review the class in this folder: its prose that changed since the last commit
    python3 review.py --class DIR            the class in DIR
    python3 review.py FILE ...               the changes in these files, such as a commit message in a file
    python3 review.py --all FILE ...         these files whole
    python3 review.py ... --repo DIR         the reviewer may also read the project in DIR, to check what the text says of it

style/check.py checks the form of the text: the length of a sentence, a vague word, a colon between clauses. It
cannot judge whether a reader can follow the text. This script asks a model, through `claude -p`, headless. The
model gets style/REVIEW.md (the reviewer's prompt, the same for every class), the guide, the glossary and the
text. It may read the class folder, walk-kit, and the project, and nothing else. It returns each sentence that a
reader of 12 cannot follow, or that is wrong, with a rewrite. A text that passed is kept in a cache, so a second
run of the same text costs nothing.

A file is reviewed at most 3 times between two commits. Each review adds its findings to the file's report in
review-findings/ at the top of the class folder, at the file's path with .md added. The author writes `- Fixed: ...`
under each finding that the author fixed. A finding left without one is for the owner of the class. The first two
reviews fail on a finding. The third passes, and the file is not reviewed again until the next commit.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from style import prose_files

KIT = Path(__file__).resolve().parent.parent
STYLE = KIT / "style"
CACHE = Path.home() / ".cache" / "walk-kit" / "style-review"
MODEL = "opus"
TOOLS = "Read,Grep,Glob"
ROUNDS = 3  # the review of a file fails at most this many times between two commits; then its findings go to a shadow file
FINDINGS = "review-findings"  # the folder of the shadow files, at the top of the class folder; a class ignores it in git

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "fail"]},
        "findings": {"type": "array", "items": {"type": "object", "properties": {
            "file": {"type": "string"},
            "quote": {"type": "string", "description": "The words at fault, as written"},
            "problem": {"type": "string", "description": "What a reader of 12 cannot follow, or what is wrong, and why"},
            "rewrite": {"type": "string", "description": "The text as it should read"},
        }, "required": ["file", "quote", "problem", "rewrite"]}},
    },
    "required": ["verdict", "findings"],
}


def git(
    folder: Path,  # A folder in the repository
    *args: str,  # Arguments to git
) -> str:  # What git printed
    "Run git in a folder."
    return subprocess.run(["git", *args], cwd=folder, capture_output=True, text=True, check=True).stdout


def text_of(
    path: Path,  # A file
    whole: bool,  # True for the whole file, False for its change since the last commit
) -> str | None:  # The text to review, with the file's name; None if the file did not change
    """Give a file's change since the last commit, or the whole file if git does not track it or if `whole` is set."""
    if not whole:
        try:
            tracked = bool(git(path.parent, "ls-files", "--", path.name).strip())
        except subprocess.CalledProcessError:   # not in a repository
            tracked = False
        if tracked:
            diff = git(path.parent, "diff", "-U4", "HEAD", "--", path.name)
            return f"--- {path} (a diff: review the + lines) ---\n{diff}" if diff else None
    return f"--- {path} (the whole file) ---\n" + path.read_text(encoding="utf-8")


def review(
    text: str,  # The text to review, from text_of
    folders: list[Path],  # The folders that the reviewer may read
) -> dict:  # The verdict and the findings
    "Ask the model for a review of the text, or take a pass from the cache."
    ask = "\n\n".join([(STYLE / "REVIEW.md").read_text(encoding="utf-8"),
                       "=== WRITING GUIDE ===\n" + (STYLE / "GUIDE.md").read_text(encoding="utf-8"),
                       "=== GLOSSARY ===\n" + (STYLE / "README.md").read_text(encoding="utf-8"),
                       "=== TEXT TO REVIEW ===\n" + text])
    key = hashlib.sha256(f"{MODEL}\n{ask}".encode()).hexdigest()
    kept = CACHE / f"{key}.json"
    if kept.is_file():
        return json.loads(kept.read_text())
    command = ["claude", "-p", "--model", MODEL, "--tools", TOOLS, "--allowedTools", TOOLS, "--output-format", "json",
               "--json-schema", json.dumps(SCHEMA)]
    for folder in folders[1:]:
        command += ["--add-dir", str(folder)]
    done = subprocess.run(command, input=ask, capture_output=True, text=True, cwd=folders[0], check=False)
    if done.returncode:
        raise SystemExit(f"review: claude failed: {(done.stderr or done.stdout).strip()[-500:]}")
    found = json.loads(done.stdout).get("structured_output")
    if not isinstance(found, dict) or "verdict" not in found:
        raise SystemExit(f"review: claude gave no verdict: {done.stdout[-500:]}")
    if found["verdict"] == "pass" and not found["findings"]:   # only a pass is kept: a failed text is reviewed again
        CACHE.mkdir(parents=True, exist_ok=True)
        kept.write_text(json.dumps(found))
    return found


def shadow(
    path: Path,  # A reviewed file
    folder: Path,  # The class folder
) -> Path:  # Its shadow file in review-findings, at the same path with .md added
    "Name the shadow file of a reviewed file."
    name = str(path.relative_to(folder)) if path.is_relative_to(folder) else str(path).lstrip("/")
    return folder / FINDINGS / f"{name}.md"


def head(
    path: Path,  # A file
) -> str:  # The last commit of the repository that holds it, or "none"
    "Name the last commit of the file's repository."
    try:
        return git(path.parent, "rev-parse", "HEAD").strip()
    except subprocess.CalledProcessError:
        return "none"


def round_of(
    path: Path,  # A reviewed file
    kept: Path,  # Its shadow file
) -> int:  # The number of this review of the file since the last commit, from 1
    "Count the reviews of a file that had findings since the last commit, from the report's header. A pass does not count."
    lines = kept.read_text(encoding="utf-8").splitlines()[:3] if kept.is_file() else []
    if f"commit: {head(path)}" not in lines:
        return 1
    return next((int(line.split()[1]) for line in lines if line.startswith("round: ")), 0) + 1


NOTE = "The author writes `- Fixed: ...` under each finding that the author fixed. A finding with no Fixed line is for the owner."


def keep(
    path: Path,  # A reviewed file
    kept: Path,  # Its report
    number: int,  # The number of this review
    findings: list[dict],  # Its findings
) -> None:
    """Add the findings of a review to the file's report, one file for each reviewed file. A report counts from the last
    commit: after a new commit, the first review starts a new report."""
    old = kept.read_text(encoding="utf-8") if kept.is_file() else ""
    rounds = old.split("\n\n", 1)[1] if f"commit: {head(path)}" in old.splitlines()[:3] and "\n\n" in old else ""
    body = "\n".join(f"## \"{f['quote']}\"\n\n- Problem: {f['problem']}\n- Rewrite: {f['rewrite']}\n" for f in findings)
    section = f"# Round {number}\n\n{body or 'No findings.'}\n"
    kept.parent.mkdir(parents=True, exist_ok=True)
    kept.write_text(f"round: {number}\ncommit: {head(path)}\nfile: {path}\n\n{NOTE}\n\n{rounds.removeprefix(NOTE + chr(10) + chr(10))}{section}",
                    encoding="utf-8")


def run(
    files: list[Path],  # The files to review
    whole: bool,  # True to review them whole, False for their changes since the last commit
    folders: list[Path],  # The folders that the reviewer may read, the first one its working folder
) -> int:  # The number of findings
    "Review each file, print each finding and the file's result, and count the findings."
    if files and not shutil.which("claude"):
        print("review: skipped, because claude (Claude Code) is not installed")
        return 0
    count = 0
    for path in files:
        kept = shadow(path, folders[0])
        number = round_of(path, kept)
        if number > ROUNDS:   # its findings wait in its shadow file for a person, until the next commit
            print(f"{path}: round {ROUNDS} of the review is done; its findings are in {kept}")
            continue
        text = text_of(path, whole)
        if text is None:   # no change since the last commit
            continue
        found = review(text, folders)
        if not found["findings"]:   # a pass is not a round: the next change is reviewed again
            print(f"{path}: pass (review)")
            continue
        keep(path, kept, number, found["findings"])
        if number == ROUNDS:   # the last round: the findings go to a person, and the check passes
            print(f"{path}: round {ROUNDS} of the review, {len(found['findings'])} findings left in {kept}")
            continue
        for finding in found["findings"]:
            count += 1
            print(f"{finding['file']}: \"{finding['quote']}\"\n  problem: {finding['problem']}\n  rewrite: {finding['rewrite']}\n")
        print(f"{path}: FAIL (review, round {number} of {ROUNDS})")
    return count


def main() -> int:  # The exit code: 1 if there is a finding
    """Review the changed prose of a class, or the given files."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--class", dest="folder", type=Path, default=Path("."), help="the class folder (default: this folder)")
    parser.add_argument("--repo", type=Path, help="the project, which the reviewer may read")
    parser.add_argument("--all", action="store_true", help="review the files whole, not only their change")
    parser.add_argument("files", nargs="*", type=Path, help="files to review in place of the class's prose")
    args = parser.parse_args()
    folder = args.folder.expanduser().resolve()
    files = [path.resolve() for path in args.files] if args.files else prose_files(folder)[0]
    folders = [folder, KIT] + ([args.repo.expanduser().resolve()] if args.repo else [])
    count = run(files, args.all, folders)
    if count:
        print(f"review: {count} findings", file=sys.stderr)
    return 1 if count else 0


if __name__ == "__main__":
    sys.exit(main())
