"""Render the pages that students read from the facts of a walk, which `timewalk-export --json` writes.

    python3 render.py FACTS.json --markdown walks/ID --site site      write the pages of one walk
    python3 render.py FACTS.json --check                              check the walk's text, and write nothing
    python3 render.py --class . --repo ../bla --github URL            check every walk of a class, for just check
    python3 render.py --class . --repo ../bla --github URL --pages DIR    write the pages of every walk of a class, for just pages

A tutorial has two ways of reading, from one set of facts. **Read the tutorial** explains each change, with the code to
look at: it is timewalk's watch mode. **Build it yourself** gives every command to run and every change to make by
hand: it is do mode. A narrative has one, Read the tutorial.

Each page has two kinds of text. The author's text explains, and goes on the page as written, every line of it. A
`patch$` line becomes a link to the file's diff, and in Build it yourself also the command that applies the patch from
GitHub. The renderer's text comes from the facts: under each change, a
section **What changed** lists every file with its words, its line counts, the do$ line that makes it and a link to the
file, then the whole diff of each file, folded, then the links to the change on GitHub and to the code after it. In Build
it yourself, each patch is open: the whole diff of a file that no do$ line makes, and the lines changed after the do$
line that makes one. timewalk runs the do$ lines to say which files they make. It is the same in every part, so a reader
learns it once. The renderer's own words never name timewalk's steps, moves or commits, and its numbers are timewalk's.

`--markdown DIR` writes `read.md` and `build.md` (a narrative: `read.md`), for GitHub. `--site DIR` writes a website for
smalldocs: `index.qmd`, which explains the two ways, a page for each part in `read/` and `build/`, `_smalldocs.yml` and
`styles.css`. Every file it writes says so in its first line, and it writes over only such files, and removes its own
pages that the walk no longer has. The same facts give the same bytes.

`--pages DIR` writes the pages of every walk of a class into DIR as walk-update lays them out in the walk repository:
`walks/ID/` for the Markdown, `site/` for the first walk's website and `sites/ID/` for the others, and `walks/README.md`.

`--check` reports facts made without running the do$ lines, and the words of timewalk in the text that a reader sees. `--class` does the same for every walk that gets pages, with the facts from timewalk, and
also checks the rendered pages against the writing guide. The exit code is 1 if it finds a problem. `walk_update.py`
renders with the same functions, and says how many problems there are.
"""

import argparse
import fnmatch
import hashlib
import json
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

MADE = "Made by the walk skill's render.py from the facts of the walk. Do not edit it by hand: run just walk-update again."
FORMATS = (3,)  # the versions of the facts' layout that this script reads
WAYS = {
    "watch": ("Read the tutorial", "read", "Each change explained, with the code to look at."),
    "do": ("Build it yourself", "build", "Every command to run and every change to make by hand, to make the project yourself."),
}
WHAT_CHANGED = ("Each part ends with a section called **What changed**. It lists every file that the part changes, with a link to "
                "the file, and then the whole diff of each file, folded. A lockfile and a binary file have a link alone. The text "
                "above it explains the change. What changed is what you check your files against.")
BY_HAND = ("In Build it yourself, a file that a command makes says which command. A diff that is open is a patch. Apply it with the "
           "command in the text, or make the same change in your editor.")
LOCKS = {"uv.lock", "poetry.lock", "Pipfile.lock", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock", "Gemfile.lock",
         "composer.lock", "go.sum", "flake.lock"}
OUR_WORDS = re.compile(r"\b(?i:steps?|commits?)\b|(?:(?<=[a-z,;:] )|(?<=[a-z,;:] \*\*)|(?<=[(\[]))Start\b")   # Start inside a sentence, bare, bold or in brackets; "Start the server" is a verb
CHANGE_OF = re.compile(r"\b([Tt]he change of) `([^`]+)`")
FENCE = re.compile(r"^\s*(```+|~~~+)")
SITE_TAKEN = {"read", "build", "site_libs"}  # folders of the first walk's built site: no other walk's site may have these ids
PAGE_GLOBS = ("walks/README.md", "walks/*/read.md", "walks/*/build.md", "site/**/*.qmd", "site/*.yml", "site/*.css",
              "sites/**/*.qmd", "sites/*/*.yml", "sites/*/*.css")  # every page that class_pages writes, for a later run to remove


def slug(
    name: str,  # A stop of the walk
) -> str:  # A name for its page
    """Make a file name for a part's page."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")


def anchor(
    *names: str,  # A move, and perhaps a file of it
) -> str:  # An id for a link inside the page
    """Make an id that a link can name: a move's name stays, so links to #step-02.1 keep working. A file's id ends with a
    short hash of its path, so two paths that differ only in odd characters never share one."""
    words = "-".join(re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-") for name in names)
    return words if len(names) == 1 else f"{words}-{hashlib.sha1(names[-1].encode()).hexdigest()[:6]}"


def span(
    text: str,  # A path or a line of code
) -> str:  # It as a Markdown code span, in more backticks than it holds, on one line
    """Quote text as code, whatever backticks it has."""
    text = text.replace("\n", " ")
    ticks = "`" * (max((len(run) for run in re.findall(r"`+", text)), default=0) + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{ticks}{pad}{text}{pad}{ticks}"


def of_mode(
    parts: list[dict],  # Parts of the facts
    mode: str,  # "do" or "watch"
) -> list[dict]:  # The parts that a reader of that mode reads
    """Keep the parts for both modes and those for one."""
    return [part for part in parts if part["mode"] in ("shared", mode)]


def outside_code(
    text: str,  # Markdown
) -> str:  # The same, with fenced code, code spans, links' addresses and HTML comments left out
    """Keep the words that a reader reads as prose."""
    lines, fence = [], None
    for line in text.split("\n"):
        mark = FENCE.match(line)
        if fence is None and mark:
            fence = mark.group(1)
            continue
        if fence is not None:
            if mark and mark.group(1)[0] == fence[0]:
                fence = None
            continue
        lines.append(line)
    words = "\n".join(lines)
    words = re.sub(r"<!--.*?-->", " ", words, flags=re.DOTALL)
    words = re.sub(r"(`+)(.+?)\1", " ", words)
    return re.sub(r"\]\([^)]*\)", "]", words)


class Page:
    """The text of one way of reading, as lines, with the links into the project on GitHub."""

    def __init__(
        self,
        facts: dict,  # The facts of the walk
        mode: str,  # "do" or "watch"
        site: bool,  # A page of the website: a part's moves are at level 2, else level 3
    ) -> None:
        """Keep what each line needs."""
        self.facts, self.mode, self.site = facts, mode, site
        self.url = github(facts)
        self.lines: list[str] = []

    def blob(
        self,
        sha: str,  # A commit
        path: str,  # A file of the project
    ) -> str:  # The file at that commit, on GitHub
        """Link to a file as a commit has it."""
        return f"{self.url}/blob/{sha}/{quote(path)}"

    def tree(
        self,
        sha: str,  # A commit
    ) -> str:  # The code at that commit, on GitHub
        """Link to the code as a commit has it."""
        return f"{self.url}/tree/{sha}"

    def add(
        self,
        *lines: str,  # Lines of Markdown; "" is a blank line between blocks, and a block of several lines comes as one string
    ) -> None:
        """Add lines. A blank line between blocks is left out after another; a block of several lines goes in as it is, so
        that the author's text and a diff keep every line, their blank lines too."""
        for line in lines:
            if not line.strip() and (not self.lines or not self.lines[-1].strip()):
                continue
            self.lines.append(line)

    def parts(
        self,
        parts: list[dict],  # The parts of a stop or a move
        sha: str,  # The commit they lead to, for a patch
        files: list[dict],  # The files of that change, for the change of a file
        move: str,  # The move, for the ids of What changed
        base: str | None = None,  # The commit before, for a part of several commits; None for one commit
    ) -> None:
        """Write the author's text: prose as written, commands as code, and a patch$ line as a link to the file's diff under
        What changed. In Build it yourself, a patch$ line also gives the command that applies the patch from GitHub."""
        known = {f["path"] for f in files}
        run: list[dict] = []   # commands one after another, written as one block

        def flush() -> None:
            if not run:
                return
            block = ["```bash"]
            for command in run:
                if command["track"] and command["track"] != "main" and not any(line.startswith("# in a second") for line in block):
                    block.append("# in a second terminal")
                elif command["track"] == "main":
                    block.append("# in the project, where you started")
                block.append(command["text"])
            self.add("", *block, "```", "")
            run.clear()

        for part in of_mode(parts, self.mode):
            if part["kind"] == "command":
                if part["makes"] and self.mode == "watch":   # what made the change: to read, not to run
                    flush()
                    self.add("", f"This change came from running `{part['text']}`.", "")
                    continue
                if part["makes"]:   # a command that makes the change: a block of its own, apart from the checks
                    flush()
                    run.append(part)
                    flush()
                    continue
                run.append(part)
                continue
            flush()
            if part["kind"] == "prose":
                text = CHANGE_OF.sub(lambda m: f"[{m.group(1)} `{m.group(2)}`](#{anchor(move, m.group(2))})" if m.group(2) in known else m.group(0),
                                     part["text"])
                self.add("", text, "")
            elif part["kind"] == "patch":
                path = part["path"]
                link = f"[{span(path)}](#{anchor(move, path)})" if path in known else span(path)
                by = next((f["by"] for f in files if f["path"] == path), "patch")
                if self.mode == "watch":
                    self.add("", f"A patch to {link}.", "")
                elif isinstance(by, int):   # a do$ line wrote the file first: the patch is what changes after it, under What changed
                    self.add("", f"Then change {link} as its patch shows.", "")
                elif any(f["path"] == path and f["binary"] for f in files):   # GitHub's diff has no binary data
                    self.add("", f"{link} is a binary file, with no patch to apply. Take it from the project:", "", "```bash",
                             f"git restore --source {sha[:12]} --worktree -- {shlex.quote(':(top,literal)' + path)}", "```", "")
                else:   # the whole change from GitHub, of which git apply takes this file alone, from the top of the project
                    diff = f"{self.url}/compare/{base}...{sha}.diff" if base else f"{self.url}/commit/{sha}.diff"
                    pattern = re.sub(r"([*?\[\\])", r"\\\1", path)   # git apply reads --include as a pattern
                    self.add("", f"Apply the patch to {link}, from the top of the project:", "", "```bash",
                             f"curl -fsSL {diff} | git apply --include={shlex.quote(pattern)}", "```", "")
        flush()

    def check(
        self,
        sha: str,  # The commit that the learner's files should now match
        before: str | None,  # The commit before it, where the learner started the move; None at the first commit
        what: str,  # "move" or "part"
    ) -> None:
        """In Build it yourself: the command that checks the learner's files against the commit, and the one that takes the
        commit's files as they are. Both run anywhere in the learner's clone of the project."""
        if self.mode != "do":
            return
        self.add("", f"Check your files against this {what}. The command prints nothing when they match, and otherwise shows what "
                 "differs:", "", "```bash", f"git check {sha[:12]}", "```", "",
                 f"If you are stuck, this command puts the files of this {what} in place of yours. A file that you made yourself "
                 "stays:", "",
                 "```bash", catch_up(before, sha), "```", "")

    def what_changed(
        self,
        level: int,  # The level of its heading
        move: str,  # The move or stop, for the ids
        files: list[dict],  # The files of the change
        items: list[dict],  # The files: items of the move, with their words
        commands: list[str],  # The do$ lines of the move, which a file's by counts in
        sha: str,  # The commit after the change
        base: str | None,  # The commit before, for a part of several commits; None for one commit, which has a page of its own
        first: bool = False,  # The first part of the walk, with nothing before it: its files are the whole project
    ) -> None:
        """Write What changed: every file, its words, counts, link and the command that makes it; each diff whole and folded;
        the change on GitHub. In Build it yourself, each patch, what is changed by hand, is open."""
        words: dict[str, dict] = {}   # two items for one file: both their words, and all their quoted lines
        for item in of_mode(items, self.mode):
            if item["move"]:
                continue
            if item["path"] in words:
                was = words[item["path"]]
                words[item["path"]] = {**was, "words": " ".join(ended(w) for w in (was["words"], item["words"]) if w.strip()), "show": was["show"] + item["show"]}
            else:
                words[item["path"]] = item
        self.add("", f"{'#' * level} What changed" + (f" {{#{anchor(move, 'what-changed')}}}" if self.site else ""), "")
        for found in files:
            path = found["path"]
            item = words.get(path)
            said = ended(item["words"]) if item and item["words"].strip() else (describe(found["names"]) + "." if describe(found["names"]) else "")
            link = "" if found["status"] == "deleted" else f" [The file]({self.blob(sha, path)})."
            source = f" It comes from {span(commands[found['by']])}." if isinstance(found["by"], int) and found["by"] < len(commands) else ""
            self.add(f"- <a id=\"{anchor(move, path)}\"></a>{span(path)}:" + (f" {said}" if said else "") + f" {counts(found)}.{source}{link}")
            for shown in item["show"] if item else []:
                self.add(f"  - look at `{shown}`" if "`" not in shown else f"  - look at ``{shown}``")
        for item in of_mode(items, self.mode):
            if item["move"]:   # a file as another part left it
                then = self.facts["history"].get(item["move"], item["move"])
                self.add(f"- `{item['path']}`" + (f", {item['words'].rstrip('.')}" if item["words"] else "") +
                         f". [The file as it was then]({self.blob(then, item['path'])}).")
        for found in files:
            if found["binary"] or not found["diff"] or found["path"].rsplit("/", 1)[-1] in LOCKS:
                continue
            path = f"<code>{escape(found['path'].replace(chr(10), ' '))}</code>"
            by, diff, summary, open_ = found["by"], found["diff"], f"The diff of {path}", ""
            if self.mode == "do" and first:
                pass   # the project as it starts: the student has it, and makes nothing by hand
            elif self.mode == "do" and by == "patch":
                summary, open_ = f"The patch to {path}", " open"
            elif self.mode == "do" and isinstance(by, int) and by < len(commands):
                command = f"<code>{escape(commands[by])}</code>"
                if found["patch"]:
                    diff, summary, open_ = found["patch"], f"After {command}, the patch to {path}", " open"
                else:
                    summary = f"The diff that {command} makes in {path}"
            fence = "`" * max(3, 1 + max((len(run) for run in re.findall(r"`+", diff)), default=0))
            self.add("", f"<details{open_}><summary>{summary}</summary>", "", "\n".join([f"{fence}diff", diff.rstrip("\n"), fence]), "", "</details>", "")
        if base is None and first:   # the first part: the project as it starts, not one commit's change
            self.add("", f"[The code]({self.tree(sha)}).", "")
            return
        change = f"{self.url}/compare/{base}...{sha}" if base else f"{self.url}/commit/{sha}"
        self.add("", f"[This change on GitHub]({change}). [The code after it]({self.tree(sha)}).", "")


def ended(
    words: str,  # The words of an item, as the author wrote them
) -> str:  # The same, with a full stop after them when they end with none, so that the line's next sentence starts apart
    """End the author's words as a sentence, without changing them."""
    words = words.strip()
    return words if not words or words[-1] in ".!?:" or words.endswith(("`", ")")) and words.rstrip("`)")[-1:] in ".!?" else words + "."


def escape(
    text: str,  # Text for HTML
) -> str:  # The same, safe inside HTML
    """Escape the characters that HTML reads."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def describe(
    names: dict,  # The names a change adds, removes and changes
) -> str:  # Them in a phrase, or ""
    """Say what a change does to the code, from its names alone."""
    phrases = [f"{verb} " + ", ".join(f"`{name}`" for name in names[key]) for verb, key in (("adds", "added"), ("changes", "changed"), ("removes", "removed"))
               if names[key]]
    return "; ".join(phrases)


def counts(
    found: dict,  # A file of a change
) -> str:  # Its kind of change and its lines, in a few words
    """Count a file's lines as a reader wants them."""
    def lines(count: int) -> str:
        return f"{count} line{'s' * (count != 1)}"

    if found["binary"]:
        return "A binary file"
    if found["status"] == "added":
        return f"New, {lines(found['added'])}"
    if found["status"] == "deleted":
        return "Deleted"
    if found["status"] == "modified" and not found["added"] and not found["removed"]:
        return "Its lines stay as they were"   # a change of mode alone, such as chmod +x
    change = f"{lines(found['added'])} added, {found['removed']} removed" if found["removed"] else f"{lines(found['added'])} added"
    if found["status"] == "renamed":
        return f"Renamed from `{found['old_path']}`" + (f", {change}" if found["added"] or found["removed"] else "")
    return change[0].upper() + change[1:]


def stop_page(
    facts: dict,  # The facts of the walk
    stop: dict,  # One stop
    at: int,  # Its place, from 1
    mode: str,  # "do" or "watch"
    site: bool,  # A page of the website, with the stop as its title
) -> list[str]:  # The stop's text, from its heading
    """Write one part of the walk in one way of reading."""
    page = Page(facts, mode, site)
    top = 1 if site else 2
    if not site:
        page.add(f'<a id="{anchor(stop["name"])}"></a>', "", f"{'#' * top} {stop['number']} {stop['title']}".rstrip(), "")
    before = facts["stops"][at - 2]["commit"] if at > 1 else None
    if mode == "do" and stop["start"] and before and stop["start"] != before:   # the walk skips commits: the learner takes them
        page.add("", "This part does not start where the part before it ends, because the walk skips some changes. This command "
                 "puts the files that this part starts from in place of yours. Run it, and then go on:", "", "```bash", catch_up(before, stop["start"]), "```", "")
    if site and mode == "do" and stop["start"]:   # a page of its own: a reader may start here
        page.add("", "If you start at this part, make your clone as **Get the project** says, and then run this command. It puts "
                 "in your clone the files that this part starts from. A file that the project deleted before this part stays, so "
                 "delete it if `git check` lists it:", "",
                 "```bash", catch_up(None, stop["start"]), "```", "")
    page.parts(stop["parts"], stop["commit"], stop["files"], stop["name"], stop["start"] if not stop["moves"] else None)
    if not stop["moves"] and stop["start"]:
        page.check(stop["commit"], stop["start"], "part")
    if stop["moves"]:
        before = f"[The code before this part]({page.tree(stop['start'])}). " if stop["start"] else ""
        page.add("", f"{before}[The code after it]({page.tree(stop['commit'])}).", "")
    else:
        items = [p for p in stop["parts"] if p["kind"] == "item"]
        page.what_changed(top + 1, stop["name"], stop["files"], items, [], stop["commit"], stop["start"], first=not stop["start"])
    for number, move in enumerate(stop["moves"]):
        level = top + 1
        heading = f"{'#' * level} {move['number']} {move['title']}".rstrip()
        if site:
            page.add("", f"{heading} {{#{anchor(move['name'])}}}", "")
        else:
            page.add("", f'<a id="{anchor(move["name"])}"></a>', "", heading, "")
        page.parts(move["parts"], move["commit"], move["files"], move["name"])
        page.check(move["commit"], stop["moves"][number - 1]["commit"] if number else stop["start"], "move")
        commands = [p["text"] for p in move["parts"] if p["kind"] == "command" and p["makes"]]
        page.what_changed(level + 1, move["name"], move["files"], [p for p in move["parts"] if p["kind"] == "item"], commands, move["commit"], None)
    return page.lines


def github(
    facts: dict,  # The facts of the walk
) -> str:  # The project's address on GitHub, with no / or .git at the end
    "Find the project's address on GitHub."
    return facts["walk"]["github"].rstrip("/").removesuffix(".git")


def catch_up(
    before: str | None,  # The commit where the learner's files were meant to be; None if unknown
    sha: str,  # The commit to take the files of
) -> str:  # The command, for the learner's clone
    """Make the command that puts the files of a commit in place of the learner's. git restore takes away each file that
    the index has and the commit does not: so the index first gets the files of the commit before, and the learner's own
    files stay. Without that commit, the index is first emptied, so no file goes: a file that the project deleted before
    stays, and the check lists it."""
    first = f"git restore --source {before[:12]} --staged -- :/" if before else "git rm -rq --cached --ignore-unmatch -- :/"
    return f"{first} && git restore --source {sha[:12]} --staged --worktree -- :/"


# Cut each requirement of a pyproject.toml to its name, its extras and its marker, as timewalk's loose does
NAMES = r"""sed -E 's/^([[:space:]]*\"[A-Za-z0-9_.-]+(\\[[^]]*\\])?)[^\";]*/\\1/'"""


def loose_kinds(
    facts: dict,  # The facts of a tutorial
) -> tuple[list[str], list[str], list[str]]:  # The globs of loose for pyproject.toml files, for uv.lock files, and for the rest
    """Sort the globs of the walk's loose by the file that each names, by its last part, as timewalk does: a pyproject.toml
    in any folder matches by the names of its packages, and so does a uv.lock."""
    loose = facts["walk"].get("loose") or []
    last = {glob: glob.rsplit("/", 1)[-1] for glob in loose}
    names = [glob for glob in loose if fnmatch.fnmatchcase("pyproject.toml", last[glob])]
    lock = [glob for glob in loose if glob not in names and fnmatch.fnmatchcase("uv.lock", last[glob])]
    return names, lock, [glob for glob in loose if glob not in names and glob not in lock]


def check_lines(
    facts: dict,  # The facts of a tutorial
) -> list[str]:  # The commands that set up git check in the learner's clone
    """Make the commands that add `git check SHA` to the learner's clone. Without `loose`, it stages every file and lists the
    files that differ from the commit. With `loose`, it compares each pyproject.toml that loose names by the names of its
    packages, leaves the lines of a uv.lock out but runs `uv lock --check`, and checks only that any other file that loose
    names is there, as timewalk does."""
    names, lock, other = loose_kinds(facts)
    skipped = lock + other   # their lines are not compared
    if not (names or skipped):
        body = 'git add -A && git diff --cached --stat "$1"'
    else:
        body = 'git add -A && git diff --cached "$1" -- ":/"' + "".join(f' ":(top,exclude,glob){glob}"' for glob in skipped)
        if skipped:   # the project's copy and the learner's are both there, or both not
            body += ' && git diff --cached --name-status --diff-filter=AD "$1" --' + "".join(f' ":(top,glob){glob}"' for glob in skipped)
        if lock:   # the learner's uv.lock fits the learner's pyproject.toml
            body += ' && { [ ! -f uv.lock ] || uv lock --check -q; }'
    lines = [f"git config alias.check '!f() {{ {body}; }}; f'"]
    if names:   # a glob with no / names a file at the top, as in timewalk; git's attributes would match it in any folder
        attributes = [f"echo '{glob if '/' in glob else '/' + glob} diff=names' >> .git/info/attributes" for glob in names]
        lines = [*attributes, f'git config diff.names.textconv "{NAMES}"', *lines]
    return lines


def clone_lines(
    facts: dict,  # The facts of a tutorial
    level: int,  # The level of its heading
) -> list[str]:  # How to get the project, for Build it yourself
    """Say how to get a clone of the project, at the commit where the walk starts: Build it yourself runs in it."""
    if not facts["stops"]:
        return []
    first = facts["stops"][0]
    start = (first["start"] or first["commit"])[:12]
    name = github(facts).rsplit("/", 1)[-1]
    names, lock, _ = loose_kinds(facts)
    note = (" It compares `pyproject.toml` by the names of its packages, so another version of a package does not count as a "
            "difference." if names else "")
    if lock:   # check_lines leaves out uv.lock's lines, and runs uv lock --check
        note += (" It does not compare the lines of `uv.lock`. It checks that you and the project both have a `uv.lock`, or both "
                 "have none. It also checks that your `uv.lock` is up to date with your `pyproject.toml`.")
    clone = ("You build the project in a clone of your own, on a branch `mine` that starts where this walk starts. Run the "
             "commands of these pages in its top folder.")
    return ["", f"{'#' * level} Get the project", "", clone, "",
            "```bash", f"git clone {github(facts)}", f"cd {name}", f"git switch -c mine {start}", "```", "",
            "Then add the command `git check`, which compares your files with the project's after each move." + note, "",
            "```bash", *check_lines(facts), "```", ""]


def intro_lines(
    facts: dict,  # The facts of the walk
    mode: str,  # "do" or "watch"
) -> list[str]:  # The walk's intro, in that way of reading
    """Write the walk's intro."""
    page = Page(facts, mode, False)
    first = facts["stops"][0] if facts["stops"] else None
    page.parts(facts["intro"], first["commit"] if first else "", [], "intro")
    return page.lines


def ways(
    facts: dict,  # The facts of the walk
) -> list[str]:  # The modes it has: do and watch for a tutorial, watch for a narrative
    """List the ways of reading a walk."""
    return ["watch", "do"] if facts["walk"]["kind"] == "tutorial" else ["watch"]


def markdown_files(
    facts: dict,  # The facts of the walk
) -> dict[str, str]:  # read.md, and build.md for a tutorial
    """Write each way of reading as one Markdown file, for GitHub."""
    files = {}
    for mode in ways(facts):
        name, file, what = WAYS[mode]
        lines = [f"<!-- {MADE} -->", "", f"# {facts['walk']['title']}", "", f"**{name}.** {what}"]
        other = [m for m in ways(facts) if m != mode]
        if other:
            lines[-1] += f" [{WAYS[other[0]][0]}]({WAYS[other[0]][1]}.md) is the other way to read it."
        lines += ["", WHAT_CHANGED, *(["", BY_HAND] if mode == "do" else []), ""]
        intro = [*intro_lines(facts, mode), ""]
        clone = clone_lines(facts, 2) if mode == "do" else []
        if any(p["kind"] == "command" for p in of_mode(facts["intro"], mode)):   # the intro's commands run in the clone
            lines += clone + intro
        else:
            lines += intro + clone
        for at, stop in enumerate(facts["stops"], 1):
            lines += [*stop_page(facts, stop, at, mode, False), ""]
        files[f"{file}.md"] = squeeze(lines)
    return files


def site_files(
    facts: dict,  # The facts of the walk
) -> dict[str, str]:  # Each file of the website, by its path in the site's folder
    """Write the website: a front page that explains the ways of reading, and a page for each part in each way."""
    title = facts["walk"]["title"]
    files: dict[str, str] = {}
    front = [f"<!-- {MADE} -->", "", *intro_lines(facts, "watch"), ""]
    sidebar = ["      - index.qmd"]
    if len(ways(facts)) > 1:
        front += ["There are two ways to read this tutorial. Both have the same parts, in the same order.", ""]
    front += [WHAT_CHANGED, "", *([BY_HAND, ""] if len(ways(facts)) > 1 else [])]
    for mode in ways(facts):
        name, folder, what = WAYS[mode]
        front += [f"## {name}", "", what, ""]
        if mode == "do" and facts["stops"]:
            front += [*clone_lines(facts, 3), "### The parts", ""]
        sidebar += [f"      - section: {json.dumps(name)}", "        contents:"]
        for at, stop in enumerate(facts["stops"], 1):
            label = f"{stop['number']} {stop['title']}".strip()
            page = f"{folder}/{slug(stop['name'])}.qmd"
            switch = ""
            for other in (m for m in ways(facts) if m != mode):
                switch = f"**{name}.** [{WAYS[other][0]}](../{WAYS[other][1]}/{slug(stop['name'])}.qmd) is the other way to read this part.\n\n"
            body = squeeze(stop_page(facts, stop, at, mode, True))
            files[page] = f"---\ntitle: {json.dumps(label)}\n---\n\n<!-- {MADE} -->\n\n{switch}{body}"
            text = re.sub(r"([\\\[\]])", r"\\\1", label)
            front.append(f"- [{text}]({page})")
            if stop["moves"]:
                sidebar += [f"          - section: {json.dumps(label)}", f"            href: {page}", "            contents:"]
                sidebar += [f"              - text: {json.dumps((m['number'] + ' ' + m['title']).strip())}\n"
                            f"                href: {page}#{anchor(m['name'])}" for m in stop["moves"]]
            else:
                sidebar += [f"          - text: {json.dumps(label)}\n            href: {page}"]
        front.append("")
    files["index.qmd"] = f"---\ntitle: {json.dumps(title)}\n---\n\n" + squeeze(front)
    pages = ", ".join(json.dumps(p) for p in ["index.qmd", *(f"{WAYS[m][1]}/*.qmd" for m in ways(facts))])
    files["_smalldocs.yml"] = "\n".join([
        f"# {MADE}", "project:", "  type: website", "  output-dir: _site", f"  render: [{pages}]   # only these pages", "",
        "website:", f"  title: {json.dumps(title)}", "  page-navigation: true", "  search: true", "  sidebar:", "    style: docked",
        "    contents:", *sidebar, "", "theme: cosmo", "css: styles.css", "toc: true", "toc-depth: 2", "code-copy: true",
        "from: markdown-tex_math_dollars-smart  # a $ is a dollar, not mathematics; -- stays two hyphens", ""])
    files["styles.css"] = (f"/* {MADE} */\n/* Inline code keeps the code font, without the shaded box and the colour the theme gives it. */\n"
                           "code:not(pre code) {\n  background-color: transparent !important;\n  color: inherit !important;\n"
                           "  padding: 0 !important;\n}\n/* What changed: the diffs fold, and open one at a time. */\n"
                           "details { margin: 0.5em 0; }\ndetails > summary { cursor: pointer; }\n")
    return files


def squeeze(
    lines: list[str],  # Lines of Markdown, as Page.add keeps them: "" between blocks, and a block of several lines as one string
) -> str:  # One text, with one blank line at most between blocks, and a line end at the end
    """Join the blocks with one blank line between them. A block keeps every line it has, its blank lines too."""
    out: list[str] = []
    for line in lines:
        if not line.strip():
            if out and out[-1].strip():
                out.append("")
            continue
        out.append(line)
    while out and not out[-1].strip():
        out.pop()
    return "\n".join(out) + "\n"


def source_gaps(
    facts: dict,  # The facts of a tutorial
) -> list[str]:  # Why Build it yourself cannot say how each file is made
    """Check that Build it yourself can say how a student makes each file: a do$ line writes it, or the student changes it
    by hand from its patch. timewalk runs the do$ lines to see which files they write; facts made with --no-run do not
    say, so the page shows each whole diff instead. Where a file comes from is timewalk-check's to judge."""
    if facts.get("observed"):
        return []
    moves = [move["name"] for stop in facts["stops"] for move in stop["moves"]
             if any(p["kind"] == "command" and p["makes"] for p in move["parts"])]
    if not moves:
        return []
    count = f"{len(moves)} part{'s' * (len(moves) != 1)}"
    return [f"{moves[0]}: the do$ lines did not run, so Build it yourself cannot say which files they make ({count}); make the facts without --no-run"]


def our_words(
    facts: dict,  # The facts of a walk
) -> list[str]:  # Each place where the text that a reader sees uses timewalk's words
    """Find step, commit and Start in the prose that a reader reads, outside headings, code and links. "move" is the
    reader's word too, once the intro of a tutorial has said what a move is."""
    problems = []
    places = [("the intro", facts["intro"])] + [(stop["name"], stop["parts"]) for stop in facts["stops"]] + [
        (move["name"], move["parts"]) for stop in facts["stops"] for move in stop["moves"]]
    places += [(stop["name"], [{"kind": "prose", "mode": "shared", "text": stop["title"]}]) for stop in facts["stops"]]
    places += [(move["name"], [{"kind": "prose", "mode": "shared", "text": move["title"]}]) for stop in facts["stops"] for move in stop["moves"]]
    for where, parts in places:
        for part in parts:
            text = part.get("words", "") if part["kind"] == "item" else part.get("text", "") if part["kind"] == "prose" else ""
            for line in outside_code(text).split("\n"):
                if line.lstrip().startswith("#"):
                    continue
                found = OUR_WORDS.search(line)
                if found:
                    problems.append(f"{where}: \"{found.group(0)}\" in: {line.strip()[:100]}")
    return problems


def page_walks(
    source: Path,  # The class's toc.toml
) -> list[dict]:  # The walks that get pages, as toc.toml writes them
    """Choose the walks that get pages: every walk but one that takes the same notes and the same part of the history as a
    walk before it, which differs only in the mode it starts in."""
    import tomllib

    chosen, seen = [], set()
    for entry in tomllib.loads(source.read_text(encoding="utf-8")).get("walk", []):
        key = json.dumps({k: entry.get(k) for k in ("kind", "notes", "folder", "shared", "select", "steps", "tags", "intro")}, sort_keys=True)
        if key not in seen:
            seen.add(key)
            chosen.append(entry)
    return chosen


class PagesError(Exception):
    """A walk whose pages cannot be made, with the reason."""


def export(
    repo: Path,  # The project
    toc: Path,  # The class's toc.toml
    ident: str,  # The id of a walk
    github: str,  # The project on GitHub, https://github.com/OWNER/NAME
    scratch: Path,  # A folder for the facts file
    timewalk: str | None = None,  # Where timewalk comes from (default: common.TIMEWALK)
) -> dict:  # The facts of the walk
    """Get the facts of one walk from timewalk-export --json."""
    from common import TIMEWALK, UVX

    out = scratch / f"{ident}.json"
    done = subprocess.run([*UVX, timewalk or TIMEWALK, "timewalk-export", str(repo), "--toc", str(toc), "--walk", ident, "--json", str(out),
                           "--github", github], capture_output=True, text=True, check=False)
    if done.returncode:
        raise PagesError(f"timewalk-export --json failed for walk {ident}:\n{done.stderr.strip()}")
    return load(out)


def class_pages(
    toc: Path,  # The class's toc.toml
    repo: Path,  # The project
    github: str,  # The project on GitHub, https://github.com/OWNER/NAME
    timewalk: str | None = None,  # Where timewalk comes from (default: common.TIMEWALK)
) -> tuple[dict[str, str], int, int]:  # Each page by its path in the walk repository; the walks whose do$ lines did not run; the places with timewalk's words
    """Render the pages of every walk of a class that gets pages, as the walk repository holds them. walk-update and --pages
    both write them. It raises PagesError for a walk that timewalk cannot export, or that has errors."""
    owner, project = github.rstrip("/").removesuffix(".git").split("/")[-2:]
    site = f"https://{owner}.github.io/{project}-walk"
    pages: dict[str, str] = {}
    listed, gaps, words = [], 0, 0
    with tempfile.TemporaryDirectory() as scratch:
        for number, entry in enumerate(page_walks(toc)):
            ident = entry["id"]
            if number and ident in SITE_TAKEN:
                raise PagesError(f"walk {ident}: the first walk's site has a folder {ident}, so this walk's site cannot have that id. Give it another id")
            facts = export(repo, toc, ident, github, Path(scratch), timewalk)
            if facts["errors"]:
                raise PagesError(f"timewalk-check finds errors in walk {ident}. Run just check:\n  " + "\n  ".join(facts["errors"]))
            if facts["walk"]["kind"] == "tutorial":
                gaps += len(source_gaps(facts))
            words += len(our_words(facts))
            for name, text in markdown_files(facts).items():
                pages[f"walks/{ident}/{name}"] = text
            folder = "site" if not number else f"sites/{ident}"
            for name, text in site_files(facts).items():
                pages[f"{folder}/{name}"] = text
            on_github = ", ".join(f"[{WAYS[mode][0]}]({ident}/{WAYS[mode][1]}.md)" for mode in ways(facts))   # from walks/README.md
            listed.append(f"- **{facts['walk']['title']}**. {on_github}. [Its website]({site}/{'' if not number else ident + '/'}).")
    pages["walks/README.md"] = "\n".join([
        f"<!-- {MADE} -->", "", f"# The walks through {project}", "",
        ("Each walk is a set of pages. **Read the tutorial** explains each change, with the code to look at. **Build it yourself** "
         "gives every command to run and every change to make by hand. A narrative has the first alone."), "", *listed, ""])
    return pages, gaps, words


def check_class(
    folder: Path,  # The class folder, with toc.toml
    repo: Path,  # The project
    github: str,  # The project on GitHub
) -> int:  # The number of problems
    """Check every walk that gets pages: Build it yourself gives every file, no reader sees timewalk's words, and the
    rendered pages follow the writing guide."""
    from style import blank, checker

    check, problems = checker().check, 0
    with tempfile.TemporaryDirectory() as scratch:
        for entry in page_walks(folder / "toc.toml"):
            try:
                facts = export(repo, folder / "toc.toml", entry["id"], github, Path(scratch))
            except PagesError as error:
                print(f"walk {entry['id']}: {error}")
                problems += 1
                continue
            found = source_gaps(facts) if facts["walk"]["kind"] == "tutorial" else []
            for name, text in markdown_files(facts).items():
                page = Path(scratch) / "page.md"
                page.write_text(blank(text), encoding="utf-8")
                found += [f"{name}: {problem}" for problem in check(page)[0]]
            words = our_words(facts)   # warnings: "commit" can be a word of the lesson, as in a lesson on git
            for problem in found:
                print(f"walk {entry['id']}: {problem}")
            for word in words:
                print(f"walk {entry['id']}: warning: {word}")
            print(f"render: walk {entry['id']}: {len(found)} problems, {len(words)} warnings")
            problems += len(found)
    return problems


def write(
    plan: list[tuple[Path, dict[str, str], list[str]]],  # For each folder: its files by path, and globs of the files an earlier run made
) -> list[str]:  # The paths written or removed
    """Write the files, replacing only files that this script made, and remove its own files that the walk no longer has.
    Every file is checked before the first is written, so a refusal writes nothing."""
    def ours(path: Path) -> bool:
        return MADE in path.read_text(encoding="utf-8", errors="replace")

    stale = []
    for folder, files, globs in plan:
        for path in files:
            target = folder / path
            blocked = next((up for up in target.parents if up.exists() and not up.is_dir()), None)
            if blocked:
                raise SystemExit(f"render: {blocked} is a file where {target} needs a folder; move it away")
            if target.is_dir() or (target.exists() and not ours(target)):
                raise SystemExit(f"render: {target} exists, and render.py did not make it; move it away, or write to another folder")
        for pattern in globs:
            stale += [old for old in sorted(folder.glob(pattern)) if old.relative_to(folder).as_posix() not in files and old.is_file() and ours(old)]
    done = []
    for folder, files, _ in plan:
        for path, text in files.items():
            target = folder / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists() or target.read_text(encoding="utf-8") != text:
                target.write_text(text, encoding="utf-8")
                done.append(str(target))
    for old in stale:
        old.unlink()
        done.append(f"{old} (removed)")
    return done


def load(
    path: Path,  # A facts file
) -> dict:  # The facts
    """Read a facts file, and refuse a layout that this script does not know."""
    facts = json.loads(path.read_text(encoding="utf-8"))
    if facts.get("format") not in FORMATS:
        raise SystemExit(f"render: {path} has the facts layout {facts.get('format')!r}, and this script reads {', '.join(map(str, FORMATS))}; "
                         "update the walk skill")
    return facts


def main() -> int:  # The exit code
    """Render a walk's pages, or check its text."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("facts", type=Path, nargs="?", help="the facts of one walk, from timewalk-export --json")
    parser.add_argument("--markdown", type=Path, help="the folder for read.md and build.md")
    parser.add_argument("--site", type=Path, help="the folder for the website")
    parser.add_argument("--check", action="store_true", help="check the walk's text, and write nothing")
    parser.add_argument("--class", dest="folder", type=Path, help="check every walk of this class folder, in place of FACTS")
    parser.add_argument("--repo", type=Path, help="with --class: the project")
    parser.add_argument("--github", help="with --class: the project on GitHub, https://github.com/OWNER/NAME")
    parser.add_argument("--pages", type=Path, help="with --class: write the pages of every walk into this folder, and check nothing")
    args = parser.parse_args()
    if args.folder:
        if not (args.repo and args.github):
            parser.error("--class needs --repo and --github")
        if not (args.folder / "toc.toml").is_file():
            print("render: the pages need a toc.toml, and this class has none, so there is nothing to check")
            return 0
        if args.pages:
            try:
                pages, gaps, words = class_pages(args.folder.resolve() / "toc.toml", args.repo.expanduser().resolve(), args.github)
            except PagesError as error:
                print(f"render: {error}", file=sys.stderr)
                return 1
            done = write([(args.pages, pages, list(PAGE_GLOBS))])
            print("\n".join(f"  {path}" for path in done) or "  nothing changed")
            if gaps or words:
                print(f"render: the pages have {words} places with timewalk's words, and {gaps} walks whose do$ lines did not run; just check lists them")
            return 0
        return 1 if check_class(args.folder.resolve(), args.repo.expanduser().resolve(), args.github) else 0
    if not args.facts:
        parser.error("give FACTS, or --class")
    facts = load(args.facts)
    if args.check:
        problems = source_gaps(facts) if facts["walk"]["kind"] == "tutorial" else []
        words = our_words(facts)
        for problem in problems:
            print(f"walk {facts['walk']['id']}: {problem}")
        for word in words:
            print(f"walk {facts['walk']['id']}: warning: {word}")
        print(f"render: walk {facts['walk']['id']}: {len(problems)} problems, {len(words)} warnings")
        return 1 if problems else 0
    if not args.markdown and not args.site:
        parser.error("give --markdown, --site, both, or --check")
    plan = []
    if args.markdown:
        plan.append((args.markdown, markdown_files(facts), ["read.md", "build.md"]))
    if args.site:
        plan.append((args.site, site_files(facts), ["*.qmd", "read/*.qmd", "build/*.qmd"]))
    done = write(plan)
    print("\n".join(f"  {path}" for path in done) or "  nothing changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
