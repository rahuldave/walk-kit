"""Follow a Build it yourself page as a student would, and fail if a `git check` of the page fails.

    python3 follow.py PAGE --repo DIR --work DIR [--log FILE]
    python3 follow.py PAGE ... --check-output [--report-dir DIR]      also ask a model whether the text matches what ran

PAGE is a build.md that render.py wrote, or a page of the website in build/. The script reads the page's ```bash
blocks (and ```sh and ```shell, indented in a list item or not) in order and runs each command with `sh -c` in a clone of the project, as a student types it. The clone is
made in --work, an empty scratch folder, from --repo, a local clone of the project: a `git clone https://github.com/...`
line clones --repo, into the folder that the page's `cd` names. A `curl` of a commit's or a comparison's diff on GitHub
becomes the same `git diff` in --repo, so the script needs no network for the patches.

A command that fails is logged, and is not a failure: the notes run tests that fail on purpose. Only `git check SHA`
decides. It fails if it prints anything or exits with an error. The catch-up command right after a check, `git restore
--source ... --staged ...`, runs only after that check failed, so that the next move starts from the project's files.
The command of a part that does not start where the part before it ends always runs. The script counts the `git check`
lines of the page, and fails if it ran another number of checks, or if the page has no check.

A page of the website does not have Get the project: it is in the site's index.qmd, beside the folder build/. The script
runs those commands first, with the clone at the commit where the page's "If you start at this part" command starts,
as a student who starts at that part.

With --check-output, and `claude` (Claude Code) on PATH, one call of `claude -p` gets the page and the log, with the
prompt in review/output.md. It reports each number, output or claim in the text that no output in the log shows. The
report goes to reports/follow/FOLDER-PAGE.md in --report-dir, written again at each run. A finding fails the run.

The script prints one line for each `git check`, and last `follow: N checks, M failed`. The exit code is 1 if a check
failed or the model found a problem.
"""

import argparse
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
PROMPT = KIT / "review" / "output.md"
MODEL = "opus"
TOOLS = "Read,Grep,Glob"
TIMEOUT = 900  # seconds for one command
LANGUAGES = {"bash", "sh", "shell"}  # the fences whose commands run
CHECK = re.compile(r"^\s*git check\b")  # a line of a fence that is a git check
CATCH_UP = re.compile(r"^git (?:restore --source [0-9a-f]+ --staged -- :/|rm -rq --cached --ignore-unmatch -- :/) && "
                      r"git restore --source [0-9a-f]+ --staged --worktree -- :/$")  # the command that puts a commit's files in place
START_HERE = "If you start at this part"  # the text before the command that a student who starts at a part runs
CURL = re.compile(r"curl\s+-fsSL\s+(?P<url>https://github\.com/[^/\s]+/[^/\s]+/(?:commit/(?P<sha>[0-9a-f]+)|compare/(?P<a>[0-9a-f]+)\.\.\.(?P<b>[0-9a-f]+))\.diff)")
SOURCE = re.compile(r"--source\s+([0-9a-f]+)\s+--staged\s+--worktree")
DELIMITER = re.compile(r"-?[ \t]*(?:'([^']*)'|\"([^\"]*)\"|\\?([^\s;&|<>()]+))")

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "fail"]},
        "findings": {"type": "array", "items": {"type": "object", "properties": {
            "quote": {"type": "string", "description": "The words of the page at fault, as written"},
            "problem": {"type": "string", "description": "What the log shows instead, or that no output in the log shows it"},
        }, "required": ["quote", "problem"]}},
    },
    "required": ["verdict", "findings"],
}


@dataclass
class Block:
    """A ```bash block of a page."""

    heading: str  # The last heading before it
    before: str  # The text between the block before it and this one
    commands: list[str] = field(default_factory=list)  # Its commands, a line each, with continued lines and here-documents joined


def heredocs(
    line: str,  # A line of shell
) -> list[str]:  # The delimiters of its here-documents, in order
    "Find the here-documents that a line starts: a `<<` outside quotes, and not a `<<<`."
    found, at, quote = [], 0, ""
    while at < len(line):
        char = line[at]
        if quote:
            if char == quote:
                quote = ""
            elif char == "\\" and quote == '"':
                at += 1
        elif char == "\\":
            at += 1
        elif char in "'\"":
            quote = char
        elif char == "#" and (at == 0 or line[at - 1] in " \t;&|("):
            break
        elif line.startswith("<<<", at):
            at += 3
            continue
        elif line.startswith("$((", at):   # arithmetic, where << is a shift
            end = line.find("))", at)
            at = len(line) if end < 0 else end + 2
            continue
        elif line.startswith("<<", at):
            word = DELIMITER.match(line, at + 2)
            if word and any(word.groups()):
                found.append(next(group for group in word.groups() if group is not None))
                at = word.end()
                continue
        at += 1
    return found


def commands_of(
    lines: list[str],  # The lines of a ```bash block
) -> list[str]:  # Its commands, without blank lines and comments
    "Split a block into commands: a line ending in a backslash and a here-document stay with their command."
    found, at = [], 0
    while at < len(lines):
        line = lines[at]
        at += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        while line.endswith("\\") and at < len(lines):
            line += "\n" + lines[at]
            at += 1
        for marker in heredocs(line):
            while at < len(lines):
                line += "\n" + lines[at]
                at += 1
                if lines[at - 1].strip() == marker:
                    break
        found.append(line)
    return found


def fences_of(
    text: str,  # A page in Markdown
) -> list[tuple[int, int, str, list[str]]]:  # Each fence: the line of its start, of its end, its language, and its lines
    "Find the fenced blocks of a page, indented or not, with their lines taken out of the indent of the fence."
    lines, found, at = text.split("\n"), [], 0
    while at < len(lines):
        fence = re.match(r"^([ \t]*)(`{3,}|~{3,})[ \t]*\{?\.?([\w+-]*)", lines[at])
        if not fence:
            at += 1
            continue
        indent, mark = len(fence.group(1)), fence.group(2)
        close = next((end for end in range(at + 1, len(lines))
                      if re.fullmatch(rf"[ \t]*{re.escape(mark[0])}{{{len(mark)},}}[ \t]*", lines[end])), len(lines))
        body = [line[min(indent, len(line) - len(line.lstrip(" \t"))):] for line in lines[at + 1:close]]
        found.append((at, close, fence.group(3).lower(), body))
        at = close + 1
    return found


def checks_in(
    text: str,  # A page in Markdown
) -> int:  # The number of `git check` lines in its fenced blocks of shell
    "Count the git checks that a page asks the student to run."
    return sum(1 for _, _, language, body in fences_of(text) if language in LANGUAGES for line in body if CHECK.match(line))


def blocks_of(
    text: str,  # A page in Markdown
) -> list[Block]:  # Its blocks of shell, in order
    "Find the ```bash, ```sh and ```shell blocks of a page, each with its heading and the text before it."
    lines, found, heading, since = text.split("\n"), [], "", []
    fences = {start: (close, language, body) for start, close, language, body in fences_of(text)}
    at = 0
    while at < len(lines):
        line = lines[at]
        if at in fences:
            close, language, body = fences[at]
            if language in LANGUAGES:
                found.append(Block(heading, "\n".join(since), commands_of(body)))
                since = []
            at = close + 1
            continue
        if re.match(r"^#{1,6}\s", line):
            heading, since = re.sub(r"\s*\{#[^}]*\}\s*$", "", line.lstrip("#").strip()), []
        else:
            since.append(line)
        at += 1
    return found


def section(
    blocks: list[Block],  # The blocks of a page
    title: str,  # A heading
) -> list[Block]:  # The blocks under that heading
    "Take the blocks under one heading."
    return [block for block in blocks if block.heading == title]


class Student:
    """A student at a terminal: runs the page's commands in the clone, and keeps the log."""

    def __init__(
        self,
        repo: Path,  # The local clone of the project
        work: Path,  # The scratch folder, empty
    ):
        self.repo, self.work, self.cwd = repo, work, work
        self.log: list[str] = []
        self.checks, self.failed, self.heading = 0, 0, ""
        self.groups: list[int] = []  # the process groups of the commands, killed at the end: a command may leave a server running

    def note(
        self,
        command: str,  # The command as the page gives it
        code: int,  # Its exit code
        output: str,  # What it printed
    ) -> None:
        "Add a command and its result to the log."
        text = f"$ {command}\n{output.rstrip()}".rstrip()
        fence = "`" * max([3, *(len(run) + 1 for run in re.findall(r"`+", text))])
        self.log += [f"{fence}text", text, fence, f"exit {code}", ""]

    def translate(
        self,
        command: str,  # A command of the page
    ) -> str:  # The command to run: a diff from GitHub is taken from the local clone
        "Replace a curl of a diff on GitHub by the same git diff in the local clone."
        def local(found: re.Match) -> str:
            repo = shlex.quote(str(self.repo))
            if found.group("sha"):
                return f"git -C {repo} diff --no-color --no-ext-diff {found.group('sha')}^ {found.group('sha')}"
            return f"git -C {repo} diff --no-color --no-ext-diff {found.group('a')}...{found.group('b')}"

        return CURL.sub(local, command)

    def run(
        self,
        command: str,  # A command of the page
    ) -> tuple[int, str]:  # Its exit code and what it printed
        "Run one command of the page where the student is, and log it."
        words = command.split()
        if words[:2] == ["git", "clone"]:   # the project, from the local clone, into the folder that the page's cd names
            url = next(word for word in words[2:] if not word.startswith("-"))
            name = url.rstrip("/").removesuffix(".git").rsplit("/", 1)[-1]
            done = subprocess.run(["git", "clone", "-q", str(self.repo), name], cwd=self.work, capture_output=True, text=True, check=False)
            self.note(command, done.returncode, done.stdout + done.stderr)
            if done.returncode:
                raise SystemExit(f"follow: cannot clone {self.repo}: {done.stderr.strip()}")
            return 0, ""
        if len(words) == 2 and words[0] == "cd":
            target = (self.cwd / words[1]).resolve()
            if not target.is_dir() or not target.is_relative_to(self.work.resolve()):
                raise SystemExit(f"follow: the page runs `{command}`, and {target} is not a folder in {self.work}")
            self.cwd = target
            self.note(command, 0, "")
            return 0, ""
        # The output goes to a file, not a pipe: a process that the command leaves running keeps a pipe open for ever
        with tempfile.TemporaryFile() as out:
            process = subprocess.Popen(["sh", "-c", self.translate(command)], cwd=self.cwd, stdin=subprocess.DEVNULL, stdout=out,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            self.groups.append(process.pid)
            try:
                code, late = process.wait(timeout=TIMEOUT), ""
            except subprocess.TimeoutExpired:
                kill(process.pid)
                process.wait()
                code, late = 124, f"\n(stopped after {TIMEOUT} seconds)"
            out.seek(0)
            output = out.read().decode("utf-8", errors="replace") + late
        self.note(command, code, output)
        return code, output

    def stop(self) -> None:
        "Kill every process that a command left running."
        for group in self.groups:
            kill(group)

    def check(
        self,
        command: str,  # git check SHA
    ) -> bool:  # True if it passed: no output and no error
        "Run a git check, print its result, and count it."
        code, output = self.run(command)
        self.checks += 1
        if code or output.strip():
            self.failed += 1
            print(f"FAIL {command}   ({self.heading})")
            for line in output.rstrip().split("\n")[:40]:
                print(f"     {line}")
            return False
        print(f"ok   {command}   ({self.heading})")
        return True

    def follow(
        self,
        blocks: list[Block],  # The blocks of the page, Get the project first when the page is a part of a site
        skip_start: bool,  # True when the clone already starts where this part starts
    ) -> None:
        "Run the page's commands in order: a catch-up right after a check only if the check failed, a gap always."
        passed, after_check = True, False
        for block in blocks:
            if block.heading != self.heading:
                self.heading = block.heading
                self.log += [f"## {block.heading or 'The top of the page'}", ""]
            catch_up = len(block.commands) == 1 and bool(CATCH_UP.match(block.commands[0]))
            if catch_up and after_check and passed:   # the command for a student who is stuck, after a check that passed
                after_check = False
                continue
            if catch_up and START_HERE in block.before and skip_start:
                after_check = False
                continue
            after_check = False
            for command in block.commands:
                if CHECK.match(command):
                    passed, after_check = self.check(command), True
                else:
                    self.run(command)
                    after_check = False


def kill(
    group: int,  # A process group, the pid of the command that leads it
) -> None:
    "Kill a process group, if any of it is left."
    try:
        os.killpg(group, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def report_name(
    page: Path,  # The page that was followed
) -> str:  # The path of its report in reports/follow, without .md
    """Name the report of a page, so that the pages of two walks never share a report: walks/ID/build.md gives ID-build,
    a page of the first walk's website site/build/PART.qmd gives site/build/PART, and of another's, sites/ID/build/PART.qmd,
    sites/ID/build/PART."""
    root = page.parent.parent
    if page.parent.name == "build" and (root / "index.qmd").is_file():
        return f"sites/{root.name}/build/{page.stem}" if root.parent.name == "sites" else f"site/build/{page.stem}"
    return f"{page.parent.name}-{page.stem}"


def site_start(
    page: Path,  # A page of the website, in build/
    blocks: list[Block],  # Its blocks
) -> tuple[list[Block], bool]:  # Get the project from the site's index.qmd, at the commit where the page starts; and whether it moved
    "Take Get the project from the site's front page, and start the clone where the page starts."
    index = page.parent.parent / "index.qmd"
    if not index.is_file():
        raise SystemExit(f"follow: {page} has no Get the project, and the site's {index} is missing, which has it")
    setup = section(blocks_of(index.read_text(encoding="utf-8")), "Get the project")
    if not setup:
        raise SystemExit(f"follow: {index} has no section Get the project")
    here = next((block for block in blocks if START_HERE in block.before), None)
    found = SOURCE.search("\n".join(here.commands)) if here else None
    if not found:   # the first part, which starts where the walk starts
        return setup, False
    for block in setup:
        block.commands = [re.sub(r"^git switch -c mine \S+", f"git switch -c mine {found.group(1)}", command) for command in block.commands]
    return setup, True


def check_output(
    page: Path,  # The page that was followed
    log: str,  # The log of the run
    cwd: Path,  # The student's clone, which the model may read
    report: Path,  # The report to write
) -> int:  # The number of findings
    "Ask a model whether each output and number that the page shows is in the log, and write the report."
    ask = "\n\n".join([PROMPT.read_text(encoding="utf-8"), f"=== PAGE: {page.name} ===\n" + page.read_text(encoding="utf-8"),
                       "=== LOG ===\n" + log])
    command = ["claude", "-p", "--model", MODEL, "--tools", TOOLS, "--allowedTools", TOOLS, "--output-format", "json",
               "--json-schema", json.dumps(SCHEMA)]
    done = subprocess.run(command, input=ask, capture_output=True, text=True, cwd=cwd, check=False)
    if done.returncode:
        raise SystemExit(f"follow: claude failed: {(done.stderr or done.stdout).strip()[-500:]}")
    found = json.loads(done.stdout).get("structured_output")
    if not isinstance(found, dict) or "findings" not in found:
        raise SystemExit(f"follow: claude gave no verdict: {done.stdout[-500:]}")
    findings = found["findings"]
    body = "\n".join(f"## \"{item['quote']}\"\n\n- Problem: {item['problem']}\n" for item in findings) or "No findings.\n"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(f"page: {page}\n\nThe output check of the last run of follow.py: each claim of the page that no output in the log "
                      f"shows.\n\n{body}", encoding="utf-8")
    for item in findings:
        print(f"output: \"{item['quote']}\"\n  problem: {item['problem']}")
    print(f"output check: {len(findings)} findings, in {report}")
    return len(findings)


def main() -> int:  # The exit code: 1 if a check failed or the output check found a problem
    "Follow a Build it yourself page in a scratch clone."
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("page", type=Path, help="a build.md, or a page of the website in build/")
    parser.add_argument("--repo", type=Path, required=True, help="a local clone of the project")
    parser.add_argument("--work", type=Path, required=True, help="an empty scratch folder, made if missing")
    parser.add_argument("--log", type=Path, help="write each command, its exit code and its output here, as Markdown")
    parser.add_argument("--check-output", action="store_true", help="ask a model whether the text matches the output, if claude is installed")
    parser.add_argument("--report-dir", type=Path, default=Path("."), help="the folder for reports/follow/ (default: this folder)")
    args = parser.parse_args()
    page, repo, work = args.page.resolve(), args.repo.expanduser().resolve(), args.work.expanduser().resolve()
    if not (repo / ".git").exists():
        parser.error(f"--repo {repo} is not a clone of the project")
    if work.exists() and (not work.is_dir() or any(work.iterdir())):
        parser.error(f"--work {work} is not an empty folder")
    work.mkdir(parents=True, exist_ok=True)
    text = page.read_text(encoding="utf-8")
    blocks = blocks_of(text)
    skip = False
    if not section(blocks, "Get the project"):
        setup, skip = site_start(page, blocks)
        blocks = setup + blocks
    expected = checks_in(text)
    student = Student(repo, work)
    student.log += [f"# follow.py: {page.name}", "", f"The commands of {page}, run in {work}.", ""]
    try:
        student.follow(blocks, skip)
    finally:
        student.stop()
    log = "\n".join(student.log)
    if args.log:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        args.log.write_text(log, encoding="utf-8")
    print(f"follow: {student.checks} checks, {student.failed} failed")
    missed = ""
    if not expected:
        missed = "follow: no git check on the page"
    elif student.checks != expected:
        missed = f"follow: the page has {expected} git check lines, and {student.checks} ran"
    if missed:
        print(missed)
    findings = 0
    if args.check_output:
        if shutil.which("claude"):
            report = args.report_dir.expanduser().resolve() / "reports" / "follow" / f"{report_name(page)}.md"
            findings = check_output(page, log, student.cwd, report)
        else:
            print("output check: skipped, because claude (Claude Code) is not installed")
    return 1 if student.failed or missed or findings else 0


if __name__ == "__main__":
    sys.exit(main())
