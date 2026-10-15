"""Review the prose that changed against the writing guide, with a model, and fail on any finding.

    python3 review.py                        review the class in this folder: its prose that changed since the last commit
    python3 review.py --class DIR            the class in DIR
    python3 review.py FILE ...               the changes in these files, such as a commit message in a file
    python3 review.py --all FILE ...         these files whole
    python3 review.py ... --repo DIR         the reviewer may also read the project in DIR, to check what the text says of it

style/check.py checks the form of the text: the length of a sentence, a vague word, a colon between clauses. It
cannot judge whether a reader can follow the text. This script asks a model, through `claude -p`, headless. The
model gets review/writing.md (the reviewer's prompt, the same for every class), the guide, the glossary and the
text. It may read the class folder, walk-kit, and the project, and nothing else. It returns each sentence that a
reader of 12 cannot follow, or that is wrong, with a rewrite.

Each section of the notes speaks of the project at one commit: `## step-02` at the tag step-02, `### step-02.1` at
the first commit of that step, and a stop of a walk with notes of its own at the moves that its `{{include ...}}` lines
name. With --repo, the script asks timewalk-export --json for the facts of each walk of toc.toml, with TIMEWALK_NO_RUN=1,
and takes the commits of each stop and move from them. So a walk that picks its steps has the Before that timewalk
gives it. The text sent to the model has a table of each section, its lines and its commits, and each hunk of a diff
says which section it is in. A file that no walk reads has no table. The model reads the project at a section's commit
with `git -C REPO show`, `ls-tree` and `log`, and may run no other command. A project whose path has a space is read
through a link in ~/.cache/walk-kit/repos, because the model writes the path without quotes. So a section about an
early step is not checked against later code. A text that passed is kept in a cache, so a second run of the same text
costs nothing. The files are reviewed at the same time, and their results print in order.

The presenter's private lines, which walk-update leaves out of the walk repository (see private.py: the `> Say:` and
`> Note:` cues with their blockquote, and the `time:` lines), are not reviewed: no reader but the presenter sees them.
The text sent to the model has an empty line in place of each, so the line numbers stay those of the file. A hunk of a
diff that changes only private lines, and empty lines, is left out.

A file is reviewed at most 3 times between two commits. Each review adds its findings to the file's report in
reports/writing/ at the top of the class folder, at the file's path with .md added. The author writes `- Fixed: ...`
under each finding that the author fixed. A finding left without one is for the owner of the class. The first two
reviews fail on a finding. The third passes, and the file is not reviewed again until the next commit.
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from common import TocError, toc_walks
from private import MixedCue, fenced, private_lines, toml_cues

from style import prose_files

KIT = Path(__file__).resolve().parent.parent
STYLE = KIT / "style"
PROMPT = KIT / "review" / "writing.md"  # the reviewer's prompt
CACHE = Path.home() / ".cache" / "walk-kit" / "style-review"
MODEL = "opus"
TOOLS = "Read,Grep,Glob"
GIT_VERBS = ("show", "ls-tree", "log")  # the git commands that the reviewer may run in the project, to read it at a commit
GIT_DENIED = ("Bash(*--output*)", "Bash(*--ext-diff*)")  # options of those commands that write a file or run a program
ROUNDS = 3  # the review of a file fails at most this many times between two commits; then its findings go to a shadow file
FINDINGS = Path("reports") / "writing"  # the folder of the shadow files, at the top of the class folder; a class ignores reports/writing/ in git
WORKERS = 8  # the reviews that run at the same time

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


REVIEW_GITHUB = "https://github.com/walk-kit/review"  # timewalk-export needs an address for its links; the review reads none of them
LINKS = Path.home() / ".cache" / "walk-kit" / "repos"  # a link to each project whose path has a space, for the reviewer's git commands
PLAIN = re.compile(r"[A-Za-z0-9._/+@-]+")  # a path that a shell reads as one word, with no quotes


def export(
    repo: Path,  # The project
    folder: Path,  # The class folder
    walk: dict | None,  # A walk of toc.toml, from toc_walks; None for a class with no toc.toml, whose notes.md is its walk
    scratch: Path,  # A folder for the facts file
) -> dict:  # The facts of the walk
    """Get the facts of one walk from timewalk-export --json, as render.py does, with TIMEWALK_NO_RUN=1 so that no do$ line
    runs. Raises ReviewFailed if timewalk-export fails, or writes a layout that walk-kit does not read."""
    from common import TIMEWALK, UVX
    from render import FORMATS

    name = walk["id"] if walk else "notes"
    out = scratch / f"{hashlib.sha256(name.encode()).hexdigest()[:12]}.json"
    which = ["--toc", str(folder / "toc.toml"), "--walk", name] if walk else ["--notes", str(folder / "notes.md")]
    done = subprocess.run([*UVX, TIMEWALK, "timewalk-export", str(repo), *which, "--json", str(out), "--github", REVIEW_GITHUB],
                          capture_output=True, text=True, check=False, env={**os.environ, "TIMEWALK_NO_RUN": "1"})
    if done.returncode:
        raise ReviewFailed(f"timewalk-export --json failed for walk {name}: {done.stderr.strip()[-500:]}")
    facts = json.loads(out.read_text(encoding="utf-8"))
    if facts.get("format") not in FORMATS:
        raise ReviewFailed(f"timewalk-export wrote the facts layout {facts.get('format')!r} for walk {name}, and walk-kit reads "
                           f"{', '.join(map(str, FORMATS))}")
    return facts


def walk_names(
    facts: dict,  # The facts of one walk, from export
    own: bool = True,  # False to leave out the titles of the stops of a walk with notes of its own
) -> dict[str, tuple[str, str]]:  # Each stop and move by its name, and each own stop by "## " and its title: the commit before it ("" for none) and its own
    """Name the commits of a walk's stops and moves, as timewalk gives them. A stop goes from its start to its commit; a
    move from the move before it, or the start of its stop, to its commit. A walk with notes of its own names a stop by its
    `## Title`."""
    named: dict[str, tuple[str, str]] = {}
    for stop in facts["stops"]:
        start = stop["start"] or ""
        if stop["own"] is None:
            named.setdefault(stop["name"], (start, stop["commit"]))
        elif own:
            named.setdefault(f"## {stop['own']['title']}", (start, stop["commit"]))
        before = start
        for move in stop["moves"]:
            named.setdefault(move["name"], (before, move["commit"]))
            before = move["commit"]
    return named


def walk_files(
    folder: Path,  # The class folder
    repo: Path,  # The project
) -> dict[Path, dict[str, tuple[str, str]]]:  # Each file of notes and each intro, by its path on the disk: the names of its walks, from walk_names
    """Find the walks that read each notes file and intro of a class, and the commits of their names. A file that several walks
    read takes the names of a walk that keeps every step first, then of the others in the order of toc.toml; the first walk
    that has a name gives its commits. A walk's shared notes take its moves last. Errors go to stderr, and leave the walk out."""
    toc = folder / "toc.toml"
    try:
        import tomllib

        if not toc.is_file() and not (folder / "notes.md").is_file():
            return {}
        walks = toc_walks(toc) if toc.is_file() else [None]
        entries = {entry.get("id"): entry for entry in tomllib.loads(toc.read_text(encoding="utf-8")).get("walk", [])} if toc.is_file() else {}
    except (TocError, ImportError, ValueError):   # style.py says what is wrong with toc.toml
        return {}
    every = [walk for walk in walks if walk is None or not ({"select", "steps"} & set(entries.get(walk["id"], {})))]
    ordered = every + [walk for walk in walks if walk not in every]
    with tempfile.TemporaryDirectory() as scratch, concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        jobs = [pool.submit(export, repo, folder, walk, Path(scratch)) for walk in ordered]
        files: dict[Path, dict[str, tuple[str, str]]] = {}
        shared = []
        for walk, job in zip(ordered, jobs):
            try:
                facts = job.result()
            except (ReviewFailed, OSError, ValueError, KeyError) as error:
                print(f"review: no table of commits for walk {walk['id'] if walk else 'notes.md'}: {error}", file=sys.stderr)
                continue
            read = [walk[key] for key in ("notes", "intro") if walk[key]] if walk else ["notes.md"]
            for path in read:
                named = files.setdefault((folder / path).resolve(), {})
                for name, commits in walk_names(facts).items():
                    named.setdefault(name, commits)
            if walk and walk["shared"]:
                shared.append(((folder / walk["shared"]).resolve(), walk_names(facts, own=False)))
        for path, names in shared:
            named = files.setdefault(path, {})
            for name, commits in names.items():
                named.setdefault(name, commits)
    return files


def plain_path(
    repo: Path,  # The project
) -> Path:  # A path to it that a shell reads as one word: the project's own path, or a link to it in ~/.cache/walk-kit/repos
    """Give the reviewer a path to the project with no space in it. The model writes `git -C PATH show ...` without quotes,
    and the allow rule of the command must match the path as written. A path with a space gets a link, named by a hash of
    the path, which points at the project."""
    if PLAIN.fullmatch(str(repo)):
        return repo
    link = LINKS / hashlib.sha256(str(repo).encode()).hexdigest()[:12]
    if not PLAIN.fullmatch(str(link)):
        raise ReviewFailed(f"the project {repo} has a space in its path, and so has {LINKS}, which would hold a link to it")
    if not (link.is_symlink() and link.resolve() == repo.resolve()):
        LINKS.mkdir(parents=True, exist_ok=True)
        temporary = LINKS / f".{link.name}.{os.getpid()}"
        temporary.unlink(missing_ok=True)
        temporary.symlink_to(repo)
        os.replace(temporary, link)   # at once, so that a reviewer never sees half a link
    return link


HEADING = re.compile(r"^(#{2,3})\s+(\S+)")  # a section of the notes: ## step-02 Title, ### step-02.1 Title, or ## Title of a stop


def sections(
    text: str,  # A file of notes, or any Markdown file
    named: dict[str, tuple[str, str]],  # The names of the file's walks, from walk_files
) -> list[dict]:  # Each section that names a step or a move: its heading, first and last line from 1, and its commits before and at
    """Find the commit of each section of the notes. A heading that names a stop or a move has its commits. A `## Title` stop of
    a walk with notes of its own has the commits of the stop that timewalk makes of its includes. Fenced code holds no heading."""
    lines = text.split("\n")
    code = fenced(lines)
    heads = [(at, HEADING.match(line)) for at, line in enumerate(lines) if at not in code and HEADING.match(line)]
    found, outer = [], None   # outer: the commits of the section before a ### heading, in the same ## section
    for number, (at, match) in enumerate(heads):
        end = heads[number + 1][0] if number + 1 < len(heads) else len(lines)
        commits = named.get(match.group(2))
        if commits is None and match.group(1) == "##":
            commits = named.get(f"## {lines[at][2:].strip()}")
        if match.group(1) == "###":   # a ### heading that names no move is part of the move or step before it
            commits = commits or outer
        outer = commits
        if commits:
            found.append({"heading": lines[at].strip(), "first": at + 1, "last": end, "before": commits[0], "at": commits[1]})
    return found


def table(
    path: Path,  # The file
    found: list[dict],  # Its sections, from sections
    repo: Path,  # The project
) -> str:  # The table of the commit of each section, for the model; "" if no section names a step
    "Say the commit of each section of a file, and how to read the project at it."
    if not found:
        return ""
    rows = [f"| {s['first']}-{s['last']} | {s['heading']} | {s['before'][:12] or 'none: the first step'} | {s['at'][:12]} |" for s in found]
    return "\n".join([f"=== THE COMMIT OF EACH SECTION OF {path} ===",
                      f"The project is the git repository {repo}. Each section below speaks of the project at its commit: the",
                      "section's change goes from the commit Before to the commit After. Read the project at those commits,",
                      f"never in the files of {repo}, which hold its last commit:",
                      f"    git -C {repo} show COMMIT:PATH   (a file at a commit)",
                      f"    git -C {repo} ls-tree -r --name-only COMMIT   (the files at a commit)",
                      f"    git -C {repo} log --oneline COMMIT   (the commits up to it)",
                      "Run each git command alone, with the path of the repository written out as above. A shell variable, a",
                      "loop, a pipe, `;` or `&&` makes the command refused, and so does any other command.",
                      "", "| Lines | Section | Before | After |", "|---|---|---|---|", *rows, ""])


def placed(
    diff: str,  # A diff of one file, from git diff
    found: list[dict],  # The sections of the file as it is now, from sections
) -> str:  # The diff, with a line after each hunk's header that names the sections of its changed lines
    "Say which section of the notes each hunk of a diff is in: the sections of its + lines, or of the place of its - lines."
    out, at, changed, header = [], 0, [], None   # at: the number of the next line of the new file; header: the hunk's place in out

    def mark() -> None:   # put the line that names the sections of the hunk after its header
        inside = [s["heading"] for s in found if any(s["first"] <= line <= s["last"] for line in changed)]
        out.insert(header + 1, f"=== this hunk is in the section {' and '.join(inside)} ===" if inside else "=== this hunk is in no section of the table ===")

    for line in diff.split("\n"):
        hunk = re.match(r"^@@ -\S+ \+(\d+)", line)
        if hunk:
            if header is not None and found:
                mark()
            out.append(line)
            header, at, changed = len(out) - 1, int(hunk.group(1)), []
            continue
        out.append(line)
        if header is None:
            continue
        if line.startswith("+"):
            changed.append(at)
            at += 1
        elif line.startswith("-"):
            changed.append(at)   # a removed line was where the next line of the new file is
        elif line.startswith(" "):
            at += 1
    if header is not None and found:
        mark()
    return "\n".join(out)


def hidden(
    path: Path,  # The file, for its name in a message
    text: str,  # Its text
) -> set[int]:  # The number of each private line, from 1
    """Find the lines that walk-update leaves out for students, as private.py finds them. Raises ReviewFailed for a cue
    that walk-update refuses."""
    try:
        found = private_lines(text)
    except MixedCue as mixed:
        raise ReviewFailed(f"{path}: {mixed}. walk-update refuses it; put a blank line between the two cues") from None
    if path.suffix.lower() == ".toml":   # a TOML comment such as # Say: goes to students as it is, so walk-update refuses it too
        found += toml_cues(text)
    return {at + 1 for at in found}


def blank(
    text: str,  # A file
    private: set[int],  # Its private lines, from hidden
) -> str:  # The same text, with each private line empty
    "Empty the private lines of a text, and keep every other line at its number."
    return "\n".join("" if number in private else line for number, line in enumerate(text.split("\n"), 1))


def public_diff(
    diff: str,  # A diff of one file, from git diff
    old: set[int],  # The private lines of the file at the last commit, from hidden
    new: set[int],  # The private lines of the file as it is now
) -> str | None:  # The diff with each private line empty and each hunk that changes only private lines left out; None if no hunk is left
    "Keep the private lines of a diff from the reviewer. A hunk whose other changed lines are all empty goes too."
    head, hunks = [], []   # the lines before the first hunk; each hunk as its lines, and whether it changes a public line with words
    before = after = 0   # the number of the next line of the old file and of the new file
    for line in diff.split("\n"):
        hunk = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)", line)
        if hunk:
            before, after = int(hunk.group(1)), int(hunk.group(2))
            hunks.append([[line], False])
        elif not hunks:
            head.append(line)
        elif line.startswith("-"):
            hunks[-1][0].append("-" if before in old else line)
            hunks[-1][1] |= before not in old and bool(line[1:].strip())
            before += 1
        elif line.startswith("+"):
            hunks[-1][0].append("+" if after in new else line)
            hunks[-1][1] |= after not in new and bool(line[1:].strip())
            after += 1
        elif line.startswith(" "):
            hunks[-1][0].append(" " if after in new else line)
            before, after = before + 1, after + 1
        else:   # \ No newline at end of file, or the empty end of the diff
            hunks[-1][0].append(line)
    kept = [line for lines, public in hunks if public for line in lines]
    return "\n".join(head + kept) if kept else None


def text_of(
    path: Path,  # A file
    whole: bool,  # True for the whole file, False for its change since the last commit
    named: dict[str, tuple[str, str]] | None = None,  # The names of the file's walks, from walk_files; None for a file of no walk
    repo: Path | None = None,  # The project, by the path that the reviewer reads it at, from plain_path
) -> str | None:  # The text to review, with the file's name, and the commit of each of its sections; None if the file did not change
    """Give a file's change since the last commit, or the whole file if git does not track it or if `whole` is set, without its private lines."""
    whole_text = path.read_text(encoding="utf-8")
    private = hidden(path, whole_text)
    found = sections(whole_text, named) if named and repo else []
    said = table(path, found, repo) + "\n" if found else ""
    if not whole:
        try:
            tracked = bool(git(path.parent, "ls-files", "--", path.name).strip())
        except subprocess.CalledProcessError:   # not in a repository
            tracked = False
        if tracked:
            diff = git(path.parent, "diff", "-U4", "HEAD", "--", path.name)
            if diff:
                try:
                    was = hidden(path, git(path.parent, "show", f"HEAD:./{path.name}"))
                except subprocess.CalledProcessError:   # a file added to the index, not yet in a commit
                    was = set()
                diff = public_diff(diff, was, private)
            return f"{said}--- {path} (a diff: review the + lines) ---\n{placed(diff, found)}" if diff else None
    return f"{said}--- {path} (the whole file) ---\n" + blank(whole_text, private)


class ReviewFailed(Exception):
    """The model gave no review of a file: claude failed, or gave no verdict."""


def review(
    text: str,  # The text to review, from text_of
    folders: list[Path],  # The folders that the reviewer may read
    repo: Path | None = None,  # The project, which the reviewer may read at any commit with git; None for no project
) -> dict:  # The verdict and the findings
    "Ask the model for a review of the text, or take a pass from the cache."
    ask = "\n\n".join([PROMPT.read_text(encoding="utf-8"),
                       "=== WRITING GUIDE ===\n" + (STYLE / "GUIDE.md").read_text(encoding="utf-8"),
                       "=== GLOSSARY ===\n" + (STYLE / "README.md").read_text(encoding="utf-8"),
                       "=== TEXT TO REVIEW ===\n" + text])
    key = hashlib.sha256(f"{MODEL}\n{ask}".encode()).hexdigest()
    kept = CACHE / f"{key}.json"
    if kept.is_file():
        return json.loads(kept.read_text())
    command = ["claude", "-p", "--model", MODEL, *permissions(repo), "--output-format", "json", "--json-schema", json.dumps(SCHEMA)]
    for folder in folders[1:]:
        command += ["--add-dir", str(folder)]
    try:
        done = subprocess.run(command, input=ask, capture_output=True, text=True, cwd=folders[0], check=False)
    except OSError as error:
        raise ReviewFailed(f"claude did not start: {error}") from error
    if done.returncode:
        raise ReviewFailed(f"claude failed: {(done.stderr or done.stdout).strip()[-500:]}")
    try:
        found = json.loads(done.stdout).get("structured_output")
    except (json.JSONDecodeError, AttributeError):
        found = None
    if not isinstance(found, dict) or "verdict" not in found or not isinstance(found.get("findings"), list):
        raise ReviewFailed(f"claude gave no verdict: {done.stdout[-500:]}")
    if found["verdict"] == "pass" and not found["findings"]:   # only a pass is kept: a failed text is reviewed again
        CACHE.mkdir(parents=True, exist_ok=True)
        kept.write_text(json.dumps(found))
    return found


def permissions(
    repo: Path | None,  # The project, or None
) -> list[str]:  # The options of claude that say what the reviewer may do
    """Let the reviewer read its folders, and run only `git -C REPO show`, `ls-tree` and `log` in the project. --restricted
    ignores the user's own settings and keeps the file tools in the folders. dontAsk refuses every other command."""
    tools, allowed = TOOLS, TOOLS.split(",")
    if repo:
        tools += ",Bash"
        allowed += [f"Bash(git -C {repo} {verb}:*)" for verb in GIT_VERBS]
    said = ["--restricted", "--permission-mode", "dontAsk", "--tools", tools, "--allowedTools", *allowed]
    return said + (["--disallowedTools", *GIT_DENIED] if repo else [])


def shadow(
    path: Path,  # A reviewed file
    folder: Path,  # The class folder
) -> Path:  # Its shadow file in reports/writing, at the same path with .md added
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


def one(
    path: Path,  # A file to review
    whole: bool,  # True to review it whole, False for its change since the last commit
    folders: list[Path],  # The folders that the reviewer may read, the first one its working folder
    named: dict[str, tuple[str, str]] | None = None,  # The names of the file's walks, from walk_files; None for a file of no walk
    repo: Path | None = None,  # The project, by the path that the reviewer reads it at, from plain_path
) -> tuple[str, int, bool]:  # What to print for the file, the number of findings that fail it, and True if the review failed
    "Review one file, keep its findings in its report, and say its result. A review that failed records no round."
    kept = shadow(path, folders[0])
    number = round_of(path, kept)
    if number > ROUNDS:   # its findings wait in its shadow file for a person, until the next commit
        return f"{path}: round {ROUNDS} of the review is done; its findings are in {kept}", 0, False
    try:
        text = text_of(path, whole, named, repo)
        if text is None:   # no change since the last commit
            return "", 0, False
        found = review(text, folders, repo)
    except (ReviewFailed, OSError, subprocess.CalledProcessError) as error:
        return f"{path}: FAIL (no review: {error})", 0, True
    if not found["findings"]:   # a pass is not a round: the next change is reviewed again
        return f"{path}: pass (review)", 0, False
    keep(path, kept, number, found["findings"])
    if number == ROUNDS:   # the last round: the findings go to a person, and the check passes
        return f"{path}: round {ROUNDS} of the review, {len(found['findings'])} findings left in {kept}", 0, False
    lines = [f"{finding['file']}: \"{finding['quote']}\"\n  problem: {finding['problem']}\n  rewrite: {finding['rewrite']}\n"
             for finding in found["findings"]]
    return "\n".join([*lines, f"{path}: FAIL (review, round {number} of {ROUNDS})"]), len(lines), False


def run(
    files: list[Path],  # The files to review
    whole: bool,  # True to review them whole, False for their changes since the last commit
    folder: Path,  # The class folder, the reviewer's working folder
    repo: Path | None = None,  # The project, which the reviewer may read at the commit of each section; None for no project
) -> tuple[int, list[Path]]:  # The number of findings, and the files whose review failed
    "Review the files at the same time, print each file's findings and result in the order of the list, and count the findings."
    if files and not shutil.which("claude"):
        print("review: skipped, because claude (Claude Code) is not installed")
        return 0, []
    folders = [folder, KIT] + ([repo] if repo else [])
    try:
        reader = plain_path(repo) if repo else None
    except (ReviewFailed, OSError) as error:
        print(f"review: {error}; the reviewer cannot read the project", file=sys.stderr)
        reader, folders = None, folders[:2]
    names = walk_files(folder, repo) if reader else {}
    count, failed = 0, []
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for path, (said, found, broke) in zip(files, pool.map(lambda path: one(path, whole, folders, names.get(path.resolve()), reader), files)):
            if said:
                print(said, flush=True)
            count += found
            if broke:
                failed.append(path)
    return count, failed


def main() -> int:  # The exit code: 1 if there is a finding, or a review failed
    """Review the changed prose of a class, or the given files."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--class", dest="folder", type=Path, default=Path("."), help="the class folder (default: this folder)")
    parser.add_argument("--repo", type=Path, help="the project, which the reviewer may read")
    parser.add_argument("--all", action="store_true", help="review the files whole, not only their change")
    parser.add_argument("files", nargs="*", type=Path, help="files to review in place of the class's prose")
    args = parser.parse_args()
    folder = args.folder.expanduser().resolve()
    files = [path.resolve() for path in args.files] if args.files else prose_files(folder)[0]
    count, failed = run(files, args.all, folder, args.repo.expanduser().resolve() if args.repo else None)
    if count:
        print(f"review: {count} findings", file=sys.stderr)
    for path in failed:
        print(f"review: the review of {path} failed", file=sys.stderr)
    return 1 if count or failed else 0


if __name__ == "__main__":
    sys.exit(main())
