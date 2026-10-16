"""Check a Read the tutorial page, as a reader meets it, and fail on a problem.

    python3 read_check.py PAGE... [--repo DIR] [--toc FILE] [--facts FILE] [--github]

PAGE is a page to read that render.py wrote: `walks/ID/read.md` for GitHub, or a page of a website in `read/`, in
`site/` or `site/ID/`. A narrative's pages are pages to read too. The script checks four things:

1. **Nothing to run.** The page has no `git check`, no `curl ... | git apply`, no command that takes the files of a
   commit (`git restore --source ...`), and no text of Build it yourself, such as Get the project or "Check your files
   against this". A command that made a change, a `do$` line of the notes, shows as the sentence "This change came from
   running `CMD`.", and not as a block of shell. The `do` text of the notes is not on the page.
2. **Every move is there.** The page has each part and each move of the walk, in order, with its number and its title,
   from the facts of the walk, which `timewalk-export --json` writes. A website has a page for each part. Each move's
   text of both modes and of watch mode is there, as written. Its What changed lists every file of the change, and
   each diff block holds the whole diff of that file, as the facts have it. The link to the change names its commit.
3. **Every link resolves.** A link to another page, or to an anchor `#id`, finds that page and that id. An id is
   given once in a page. With `--github`, every link to github.com answers a HEAD request with 200, and every commit
   that a link names is in `--repo`.
4. **The website builds.** smalldocs (`uvx --from 'smalldocs>=0.1.5' smalldocs render`) builds the website, one project
   in `site/`, in a scratch copy, with no error and no warning: the first walk's pages at the top, and each other
   walk's at `ID/`. Every page of the walk that `_smalldocs.yml` lists is built, and every link of every built page of
   the walk resolves there, its id too.

The facts come from `timewalk-export --json`, as render.py gets them, with the project from `--repo` and the walks
from `--toc` (by default `toc.toml` in the folder above `walks/` and `site/`). `--facts FILE` gives the facts
of one walk instead, for every page.

The script prints one line for each page and one for the websites, each problem as `PAGE:LINE: what is wrong`, and last
`read_check: N pages, M problems`. The exit code is 1 if it finds a problem.
"""

import argparse
import html
import html.parser
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render
from common import NoAddress, project_url

SMALLDOCS = ["uvx", "--from", "smalldocs>=0.1.5", "smalldocs"]
SHELL = {"bash", "sh", "shell", "console", ""}  # the fences whose lines a reader could run
RUN = [
    (re.compile(r"\bgit check\b"), "a `git check`, which belongs to Build it yourself"),
    (re.compile(r"\bcurl\b.*\|\s*git apply\b"), "a patch to apply with curl and git apply"),
    (re.compile(r"\bgit restore --source\b"), "a command that takes the files of a commit"),
    (re.compile(r"\bgit rm -rq --cached\b"), "a command that empties git's index, to start at a part"),
    (re.compile(r"\bgit switch -c mine\b"), "the branch `mine` of Build it yourself"),
    (re.compile(r"\bgit config alias\.check\b"), "the setup of `git check`"),
]  # commands that a page to read never has
DO_TEXT = [render.BY_HAND, render.CHECK_AGAINST, "Check your files against this", "If you are stuck, this command puts the files",
           "If you start at this part", "Apply the patch", "as its patch shows", "with no patch to apply",
           "because the walk skips some changes", "<details open>", "<summary>The patch to ", "<summary>After <code>"]  # renderer text of Build it yourself
# The walk preamble without its title: the notes of a walk repository start with it, and no page has it
PREAMBLE = (Path(__file__).resolve().parent.parent / "templates" / "walk" / "walk-preamble.md").read_text(encoding="utf-8").split("\n", 1)[1].strip()
MADE_BY = "This change came from running "  # the sentence that shows a do$ line on a page to read
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*(?:\{#([^}\s]+)[^}]*\})?\s*$")
LINK = re.compile(r"(?<!!)\[(?:[^\]\\]|\\.)*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)|<a\s[^>]*href=\"([^\"]+)\"|<(https?://[^>\s]+)>")
EXPLICIT_ID = re.compile(r"<a\s[^>]*(?:id|name)=\"([^\"]+)\"|\{#([^}\s]+)[^}]*\}")
GITHUB = re.compile(r"^https://github\.com/([^/]+)/([^/#?]+)(?:/(blob|tree|commit|compare)/([^/#?]+))?")
SHA = re.compile(r"^[0-9a-f]{7,40}$")
PAUSE = 0.5  # seconds between two requests to GitHub
CACHE_DAYS = 1  # how long a link that answered 200 stays answered


class Ids(html.parser.HTMLParser):
    """The ids and the links of a built page of the website."""

    def __init__(self) -> None:
        """Start with none."""
        super().__init__()
        self.ids: set[str] = set()
        self.hrefs: list[str] = []

    def handle_starttag(
        self,
        tag: str,  # The tag
        attrs: list[tuple[str, str | None]],  # Its attributes
    ) -> None:
        """Keep the tag's id, and its address if it is a link."""
        for name, value in attrs:
            if name in ("id", "name") and value:
                self.ids.add(value)
            if name == "href" and value and tag in ("a", "link"):
                self.hrefs.append(value)


def parse_html(
    path: Path,  # A built page
) -> Ids:  # Its ids and links
    "Read a built page's ids and links."
    found = Ids()
    found.feed(path.read_text(encoding="utf-8", errors="replace"))
    return found


class Text:
    """A page in Markdown, as lines, with the fences and the headings found."""

    def __init__(
        self,
        path: Path,  # The page
    ) -> None:
        """Read the page, and find its front matter, fences and headings."""
        self.path = path
        self.lines = path.read_text(encoding="utf-8").split("\n")
        self.title = None
        body = 0
        if self.lines and self.lines[0] == "---":   # front matter of a page of the website
            end = next((at for at in range(1, len(self.lines)) if self.lines[at] == "---"), 0)
            for line in self.lines[1:end]:
                if line.startswith("title:"):
                    value = line[len("title:"):].strip()
                    try:
                        self.title = json.loads(value) if value.startswith('"') else value
                    except ValueError:   # a title that smalldocs cannot read either: the build says so
                        self.title = value
            body = end + 1
        self.body = body  # the first line after the front matter
        self.fences = [(start, end, language, lines) for start, end, language, lines in fences(self.lines) if start >= body]
        inside = {at for start, end, _, _ in self.fences for at in range(start, end + 1)}
        self.prose = [at for at in range(body, len(self.lines)) if at not in inside]  # the lines outside fences
        self.headings = []  # (line, level, text, id) of each heading outside fences
        for at in self.prose:
            found = HEADING.match(self.lines[at])
            if found:
                self.headings.append((at, len(found.group(1)), found.group(2), found.group(3)))

    def where(
        self,
        at: int,  # A line, from 0
    ) -> str:  # The page and the line, for a report
        "Name a line of the page."
        return f"{self.path}:{at + 1}"


def fences(
    lines: list[str],  # The lines of a page
) -> list[tuple[int, int, str, list[str]]]:  # Each fence: the line of its start, of its end, its language, and its lines
    "Find the fenced blocks of a page, indented or not, with their lines taken out of the indent of the fence."
    found, at = [], 0
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


def code_span(
    text: str,  # Text that starts with a code span
) -> str | None:  # What the span shows, as Markdown reads it; None if the text does not start with a closed span
    "Read the code span at the start of a text."
    ticks = re.match(r"`+", text)
    if not ticks:
        return None
    close = re.search(rf"(?<!`){ticks.group(0)}(?!`)", text[ticks.end():])
    if not close:
        return None
    inner = text[ticks.end():ticks.end() + close.start()]
    return inner[1:-1] if inner.startswith(" ") and inner.endswith(" ") and inner.strip() else inner


def github_slugs(
    headings: list[str],  # The headings of a page, in order
) -> set[str]:  # The ids that GitHub gives them
    "Make the ids that GitHub gives a page's headings: lower case, without punctuation, a hyphen for each space, and -1, -2 for a repeat."
    seen: dict[str, int] = {}
    slugs = set()
    for heading in headings:
        text = re.sub(r"<[^>]+>", "", heading)
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text).replace("`", "")
        slug = re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-")
        count = seen.get(slug, 0)
        slugs.add(slug if not count else f"{slug}-{count}")
        seen[slug] = count + 1
    return slugs


def page_ids(
    text: Text,  # A page in Markdown
) -> tuple[set[str], list[tuple[int, str]]]:  # Every id that a link can name in it; and each id given twice, with its line
    "Find the ids of a page: those it gives, with <a id> and {#id}, and on GitHub those of its headings."
    given: dict[str, int] = {}
    twice = []
    for at in text.prose:
        for found in EXPLICIT_ID.finditer(text.lines[at]):
            name = found.group(1) or found.group(2)
            if name in given:
                twice.append((at, name))
            given[name] = at
    ids = set(given)
    if text.path.suffix == ".md":
        ids |= github_slugs([heading for _, _, heading, _ in text.headings])
    return ids, twice


def links_of(
    text: Text,  # A page in Markdown
) -> list[tuple[int, str]]:  # Each link outside fences and code spans, with its line
    "Find the links of a page."
    found = []
    for at in text.prose:
        line = re.sub(r"(`+).+?\1", "", text.lines[at])
        for hit in LINK.finditer(line):
            found.append((at, hit.group(1) or hit.group(2) or hit.group(3)))
    return found


def unlinked(
    text: str,  # Markdown
) -> str:  # The same, with each link to an anchor of the page as its words alone
    "Take out the links to anchors that render.py adds to the author's text, so that the text compares as written."
    return re.sub(r"\[((?:[^\]\\]|\\.)*)\]\(#[^)]*\)", r"\1", text)


def watch_parts(
    parts: list[dict],  # Parts of the facts
) -> list[dict]:  # Those that Read the tutorial shows
    "Keep the parts of both modes and of watch mode."
    return render.of_mode(parts, "watch")


class Checker:
    """The checks of the pages to read, with the facts of each walk, the websites built, and the links asked of GitHub."""

    def __init__(
        self,
        repo: Path | None,  # The project, for the facts and the commits of the links
        toc: Path | None,  # The class's toc.toml; None to find it above each page
        facts: Path | None,  # The facts of one walk, for every page; None to export them
        online: bool,  # Ask GitHub for every link to github.com
        address: str | None = None,  # The project on GitHub, https://github.com/OWNER/NAME, for timewalk-export; never guessed
    ) -> None:
        """Keep the options, and start with nothing found."""
        self.repo, self.toc, self.online = repo, toc, online
        self.address = address
        self.given = render.load(facts) if facts else None
        self.problems: list[str] = []
        self.walks: dict[tuple[str, str], dict | None] = {}  # the facts of each walk, by its toc and id
        self.sites: dict[Path, tuple[Path, str, list[str]] | None] = {}  # each walk's pages built: the website, the walk's folder in it, what smalldocs warned of them
        self.trees: dict[Path, tuple[Path, list[str]] | None] = {}  # each website built once, by its folder site/: its built tree, and what smalldocs warned
        self.parsed: dict[Path, Ids] = {}  # the ids and links of each built page read
        self.pending: list[tuple[Text, Path]] = []  # each page of a website, with its site, whose links finish() checks
        self.scratch = Path(tempfile.mkdtemp(prefix="read_check-"))
        self.answers: dict[str, int] = {}  # what GitHub answered for each link, in this run
        self.last = 0.0  # when the last request to GitHub went

    def close(self) -> None:
        """Remove the scratch folder."""
        shutil.rmtree(self.scratch, ignore_errors=True)

    def problem(
        self,
        where: str,  # The page and the line
        what: str,  # What is wrong
    ) -> None:
        """Note a problem."""
        self.problems.append(f"{where}: {what}")

    # -- where a page belongs --------------------------------------------------------------------------------------

    def place(
        self,
        page: Path,  # A page to read
    ) -> tuple[Path, str | None, Path | None]:  # The folder of the pages, the id of the walk (None: the first walk), and the website's folder
        "Find the walk of a page from its path: walks/ID/read.md, site/read/X.qmd or site/ID/read/X.qmd."
        if page.suffix == ".md":
            root, ident = page.parent.parent.parent, page.parent.name
            toc = self.toc or root / "toc.toml"
            first = render.page_walks(toc)[0]["id"] if toc.is_file() and render.page_walks(toc) else None
            if ident != first and ident.casefold() not in render.SITE_TAKEN and (root / "site" / ident / "index.qmd").is_file():
                return root, ident, root / "site" / ident
            return root, ident, root / "site" if (root / "site").is_dir() and first in (ident, None) else None
        site = page.parent.parent
        if not (site / "_smalldocs.yml").is_file() and (site.parent / "_smalldocs.yml").is_file():   # another walk's, in site/ID/
            return site.parent.parent, site.name, site
        return site.parent, None, site

    def facts_for(
        self,
        page: Path,  # A page to read
        text: Text,  # Its text
    ) -> dict | None:  # The facts of its walk; None if they cannot be had, with the problem noted
        "Get the facts of a page's walk: --facts, or timewalk-export --json, once for each walk."
        if self.given:
            return self.given
        root, ident, _ = self.place(page)
        toc = self.toc or root / "toc.toml"
        if not toc.is_file():
            self.problem(str(page), f"no toc.toml at {toc}, so the facts of the walk cannot be had; give --toc or --facts")
            return None
        if ident is None:
            walks = render.page_walks(toc)
            ident = walks[0]["id"] if walks else ""
        key = (str(toc), ident)
        if key not in self.walks:
            if not self.repo:
                self.problem(str(page), "the facts of the walk need the project: give --repo, or --facts")
                return None
            try:
                address = project_url(toc.parent, self.address)
            except NoAddress as error:
                self.problem(str(page), str(error))
                self.walks[key] = None
                return None
            try:
                self.walks[key] = render.export(self.repo, toc, ident, address, self.scratch)
            except render.PagesError as error:
                self.problem(str(page), f"walk {ident}: {error}")
                self.walks[key] = None
        return self.walks[key]

    # -- the checks --------------------------------------------------------------------------------------------------

    def check_page(
        self,
        page: Path,  # A page to read
    ) -> None:
        """Run every check on one page."""
        text = Text(page)
        self.nothing_to_run(text)
        facts = self.facts_for(page, text)
        if facts is not None:
            self.moves(text, facts)
        self.links(text)
        _, _, site = self.place(page)
        if site and site.is_dir():
            self.site(site, facts)
            if page.suffix == ".qmd":
                self.pending.append((text, site))

    def nothing_to_run(
        self,
        text: Text,  # A page to read
    ) -> None:
        """Find each command to run and each text of Build it yourself."""
        shell = {at for start, end, language, _ in text.fences if language in SHELL for at in range(start + 1, end)}
        for at in sorted(set(text.prose) | shell):
            line = text.lines[at]
            for pattern, what in RUN:
                if pattern.search(line):
                    self.problem(text.where(at), f"{what}: {line.strip()[:100]}")
            if at in shell:
                continue
            for words in DO_TEXT:
                if words in line:
                    self.problem(text.where(at), f"text of Build it yourself: {words[:60]!r}")
            heading = HEADING.match(line)
            if heading and heading.group(2) == "Get the project":
                self.problem(text.where(at), "the section Get the project, which belongs to Build it yourself")

    def moves(
        self,
        text: Text,  # A page to read
        facts: dict,  # The facts of its walk
    ) -> None:
        """Check that the page has every part and move of the walk, in order, each with its text and its diffs."""
        stops = facts["stops"]
        if text.path.suffix == ".qmd":   # a page of the website: one part
            stop = next((s for s in stops if render.slug(s["name"]) == text.path.stem), None)
            if stop is None:
                self.problem(str(text.path), f"no part of walk {facts['walk']['id']} has this page's name")
                return
            label = f"{stop['number']} {stop['title']}".strip()
            if text.title != label:
                self.problem(text.where(1), f"the title is {text.title!r}, and the part is {label!r}")
            wanted = [(2, move) for move in stop["moves"]]
            found = self.find(text, wanted)
            starts = [text.body] + [at for at, _ in found]
            self.section(text, facts, stop, starts[0], starts[1] if len(starts) > 1 else len(text.lines), stop["parts"], not stop["moves"], stop)
            for number, (at, move) in enumerate(found):
                end = starts[number + 2] if number + 2 < len(starts) else len(text.lines)
                self.section(text, facts, move, at, end, move["parts"], True, stop)
            return
        wanted = []
        for stop in stops:
            wanted += [(2, stop)] + [(3, move) for move in stop["moves"]]
        found = self.find(text, wanted)
        first = found[0][0] if found else len(text.lines)
        intro = "\n".join(text.lines[:first])
        for part in watch_parts(facts["intro"]):
            words = part["text"].strip().removeprefix(PREAMBLE).strip() if part["kind"] == "prose" else ""
            if words and unlinked(words) not in unlinked(intro):   # a walk repository's notes start with the walk preamble, which no page has
                self.problem(str(text.path), f"the intro's text is missing: {part['text'].strip()[:80]!r}")
        bounds = [at for at, _ in found] + [len(text.lines)]
        for number, (at, place) in enumerate(found):
            stop = next(s for s in stops if place is s or place in s["moves"])
            whole = place is stop and not stop["moves"]
            self.section(text, facts, place, at, bounds[number + 1], place["parts"], whole or place is not stop, stop)

    def find(
        self,
        text: Text,  # A page to read
        wanted: list[tuple[int, dict]],  # The heading level and the part or move of each heading, in order
    ) -> list[tuple[int, dict]]:  # The line of each heading found, with its part or move
        "Find the heading of each part and move in order, and note each that is missing or out of order."
        found, cursor = [], -1
        for level, place in wanted:
            title = f"{place['number']} {place['title']}".strip()
            lines = [at for at, depth, heading, _ in text.headings if depth == level and heading == title]
            after = [at for at in lines if at > cursor]
            if after:
                cursor = after[0]
                found.append((cursor, place))
            elif lines:
                self.problem(text.where(lines[0]), f"{place['name']} {title!r} is out of order")
            else:
                self.problem(str(text.path), f"{place['name']} {title!r} is missing: no heading {'#' * level} {title}")
        return found

    def section(
        self,
        text: Text,  # A page to read
        facts: dict,  # The facts of its walk
        place: dict,  # A part or a move
        start: int,  # The line of its heading
        end: int,  # The line after its section
        parts: list[dict],  # Its text
        changes: bool,  # It has a What changed of its own
        stop: dict | None = None,  # The part that holds a move
    ) -> None:
        """Check one part's or move's section: its text, its commands, its files and its diffs."""
        lines = text.lines[start:end]
        prose = unlinked("\n".join(lines))
        shown = watch_parts(parts)
        shared = [unlinked(p["text"]) for p in shown if p["kind"] == "prose"]
        for part in shown:
            if part["kind"] == "prose" and unlinked(part["text"]) not in prose:
                self.problem(text.where(start), f"{place['name']}: the text is missing, or changed: {part['text'].strip()[:80]!r}")
        for part in parts:
            words = unlinked(part.get("text", ""))
            if part["kind"] == "prose" and part["mode"] == "do" and len(words) >= 40 and not any(words in s for s in shared) and words in prose:
                self.problem(text.where(start), f"{place['name']}: text of Build it yourself: {words.strip()[:80]!r}")
        made = {}
        for at in range(start, end):
            if text.lines[at].startswith(MADE_BY) and at in text.prose:
                made[code_span(text.lines[at][len(MADE_BY):])] = at
        runnable = {line.strip() for s, e, language, body in text.fences if start <= s < end and language in SHELL for line in body}
        for part in parts:
            if part["kind"] != "command":
                continue
            if part["makes"] and part["mode"] != "do" and part["text"] not in made:
                self.problem(text.where(start), f"{place['name']}: the command that made the change, {part['text']!r}, is not shown as "
                             f"\"{MADE_BY}`...`.\"")
            also_to_read = any(p["kind"] == "command" and not p["makes"] and p["mode"] != "do" and p["text"].strip() == part["text"].strip() for p in parts)
            if (part["makes"] or part["mode"] == "do") and part["text"].strip() in runnable and not also_to_read:
                self.problem(text.where(start), f"{place['name']}: {part['text']!r} is a command to run, in a block of shell")
        for part in shown:
            if part["kind"] == "patch":
                found = next((f for f in place["files"] if part["path"] in (f["path"], f["old_path"])), None)
                path = found["path"] if found else part["path"]
                if not any(line.startswith("A patch to ") and render.span(path) in line for line in lines):
                    self.problem(text.where(start), f"{place['name']}: no \"A patch to {render.span(path)}\" for its patch$ line")
        if not changes:
            for s, _, language, _ in text.fences:
                if start <= s < end and language == "diff":
                    self.problem(text.where(s), f"{place['name']}: a diff before the first move, where the part has no What changed")
            return
        if not any(start <= at < end and heading == "What changed" for at, _, heading, _ in text.headings):
            self.problem(text.where(start), f"{place['name']}: no heading What changed")
        self.files(text, place, start, end)
        self.change_link(text, facts, place, start, end, stop)

    def files(
        self,
        text: Text,  # A page to read
        place: dict,  # A part or a move
        start: int,  # The line of its heading
        end: int,  # The line after its section
    ) -> None:
        """Check What changed: a line for each file of the change, and each file's diff as the facts have it."""
        listed = set()
        for at in range(start, end):
            item = re.match(r"^- <a id=\"[^\"]+\"></a>(`+)( ?)(.*?)\2\1:", text.lines[at])
            if item:
                listed.add(item.group(3))
        for found in place["files"]:
            if found["path"].replace("\n", " ") not in listed:
                self.problem(text.where(start), f"{place['name']}: What changed does not list {found['path']}")
        diffs: dict[str, tuple[int, str]] = {}
        for s, e, language, body in text.fences:
            if not (start <= s < end) or language != "diff":
                continue
            summary = next((text.lines[at] for at in range(s - 1, max(start, s - 4), -1) if "<summary>" in text.lines[at]), "")
            codes = re.findall(r"<code>(.*?)</code>", summary)
            if not codes:
                self.problem(text.where(s), f"{place['name']}: a diff with no summary that names its file")
                continue
            diffs[html.unescape(codes[-1])] = (s, "\n".join(body))
        expected = {}
        for found in place["files"]:
            if found["binary"] or not found["diff"] or found["path"].rsplit("/", 1)[-1] in render.LOCKS:
                continue
            expected[found["path"].replace("\n", " ")] = found["diff"].rstrip("\n")
        for path, diff in expected.items():
            if path not in diffs:
                self.problem(text.where(start), f"{place['name']}: no diff of {path}")
            elif diffs[path][1] != diff:
                self.problem(text.where(diffs[path][0]), f"{place['name']}: the diff of {path} differs from the commit's diff")
        known = {found["path"].replace("\n", " ") for found in place["files"]}
        for path, (at, _) in diffs.items():
            if path not in known:
                self.problem(text.where(at), f"{place['name']}: a diff of {path}, which the change does not have")

    def change_link(
        self,
        text: Text,  # A page to read
        facts: dict,  # The facts of its walk
        place: dict,  # A part or a move
        start: int,  # The line of its heading
        end: int,  # The line after its section
        stop: dict | None,  # The part that holds it
    ) -> None:
        """Check that the link to the change on GitHub names the change's own commits."""
        url = render.github(facts)
        section = "\n".join(text.lines[start:end])
        if place is stop and not place["start"]:   # the first part: the project as it starts
            wanted, words = f"{url}/tree/{place['commit']}", "The code"
        elif place is stop:
            wanted, words = f"{url}/compare/{place['start']}...{place['commit']}", "This change on GitHub"
        else:
            wanted, words = f"{url}/commit/{place['commit']}", "This change on GitHub"
        if f"[{words}]({wanted})" not in section:
            self.problem(text.where(start), f"{place['name']}: no link [{words}]({wanted})")

    def links(
        self,
        text: Text,  # A page to read
    ) -> None:
        """Check each id given once, each link to a page or an anchor, and with --github each link to GitHub."""
        ids, twice = page_ids(text)
        for at, name in twice:
            self.problem(text.where(at), f"the id {name!r} is given twice, so a link to #{name} finds the first")
        for at, link in links_of(text):
            if GITHUB.match(link):
                self.github(text.where(at), link)
                continue
            if re.match(r"^[a-z][a-z0-9+.-]*:", link, re.IGNORECASE):
                continue
            target, _, fragment = link.partition("#")
            if text.path.suffix == ".qmd":   # smalldocs gives ids of its own: finish() checks the id in the built page
                fragment = ""
            if not target:
                if fragment and fragment not in ids:
                    self.problem(text.where(at), f"a link to #{fragment}, which the page does not have")
                continue
            path = (text.path.parent / target).resolve()
            if not path.exists():
                self.problem(text.where(at), f"a link to {target}, which does not exist")
                continue
            if fragment and path.suffix in (".md", ".qmd") and fragment not in page_ids(Text(path))[0]:
                self.problem(text.where(at), f"a link to {target}#{fragment}, and {target} has no such id")

    def site(
        self,
        site: Path,  # The folder of a walk's website
        facts: dict | None,  # The facts of its walk
    ) -> None:
        """Build the website that holds a walk's pages once with smalldocs, in a scratch copy, and keep what it warned of the walk's pages."""
        if site in self.sites:
            return
        self.sites[site] = None
        if facts is not None:
            for stop in facts["stops"]:
                if not (site / "read" / f"{render.slug(stop['name'])}.qmd").is_file():
                    self.problem(str(site), f"no page read/{render.slug(stop['name'])}.qmd for {stop['name']}")
        project, prefix = published_place(site)
        if project not in self.trees:
            self.trees[project] = None
            copy = self.scratch / "sites" / str(len(self.trees))
            shutil.copytree(project, copy, ignore=shutil.ignore_patterns("_site"))
            try:
                done = subprocess.run([*SMALLDOCS, "render", str(copy)], capture_output=True, text=True, check=False, timeout=600)
            except (OSError, subprocess.TimeoutExpired) as error:
                self.problem(str(project), f"smalldocs could not run: {error}")
                return
            said = (done.stdout + done.stderr).strip()
            if done.returncode:
                self.problem(str(project), f"smalldocs failed: {said[-500:]}")
                return
            self.trees[project] = (copy / "_site", [line.strip() for line in said.splitlines() if re.match(r"^\s*(warning|error)\b", line, re.IGNORECASE)])
        if self.trees[project] is None:
            return
        tree, warnings = self.trees[project]
        others = other_walks(project)
        mine = [line for line in warnings if owner(warned_page(line), others) == prefix]
        self.sites[site] = (tree, prefix, mine)

    def finish(self) -> None:
        """Check the websites put together: each page that _smalldocs.yml lists is built, and each link of a built page or a page to read resolves."""
        for site, built in sorted(self.sites.items()):
            if built is None:
                continue
            tree, prefix, warnings = built
            for line in warnings:
                self.problem(str(site), f"smalldocs: {line}")
            project, _ = published_place(site)
            others = other_walks(project)
            config = (project / "_smalldocs.yml").read_text(encoding="utf-8") if (project / "_smalldocs.yml").is_file() else ""
            listed = set()
            render_list = re.search(r"^\s*render:\s*\[(.*?)\]", config, re.MULTILINE)
            for pattern in json.loads(f"[{render_list.group(1)}]") if render_list else []:
                listed |= {path.relative_to(project).as_posix() for path in project.glob(pattern)}
            listed |= set(re.findall(r"^\s*(?:-\s+|href:\s+)([^\s#:]+\.qmd)", config, re.MULTILINE))
            for page in sorted(p for p in listed if owner(p, others) == prefix):
                if not (tree / (page.removesuffix(".qmd") + ".html")).is_file():
                    self.problem(str(project / "_smalldocs.yml"), f"lists {page}, and smalldocs did not build it")
            for path in sorted((tree / prefix).rglob("*.html")):
                name = path.relative_to(tree).as_posix()
                if owner(name, others) != prefix:
                    continue   # the page of another walk, checked with that walk
                for href in self.html(path).hrefs:
                    wrong = self.resolves(tree, name, href, prefix)
                    if wrong:
                        self.problem(f"{site}/{name.removeprefix(prefix)}", f"the built page links to {href}: {wrong}")
        for text, site in self.pending:
            built = self.sites.get(site)
            if not built:
                continue
            tree, prefix, _ = built
            here = prefix + text.path.relative_to(site).with_suffix(".html").as_posix()
            for at, link in links_of(text):
                wrong = self.resolves(tree, here, re.sub(r"\.qmd(?=$|#)", ".html", link), prefix)
                if wrong:
                    self.problem(text.where(at), f"a link to {link}: {wrong}")

    def resolves(
        self,
        tree: Path,  # The websites put together, as the Pages workflow publishes them
        page: str,  # The built page that has the link, by its path in the tree
        href: str,  # The address of the link
        prefix: str,  # The folder of the page's own site in the tree, "" or "ID/"
    ) -> str | None:  # Why the link does not resolve, or None if it does
        "Resolve a link of a built page in the published tree: its page, and its id."
        if re.match(r"^[a-z][a-z0-9+.-]*:", href, re.IGNORECASE) or href.startswith("//"):
            return None
        target, _, fragment = href.partition("#")
        if target.startswith("/"):   # from the top of the website
            path = normal(target.removesuffix(".qmd") + (".html" if target.endswith(".qmd") else ""))
        else:
            path = normal((Path(page).parent / target).as_posix()) if target else page
        if target.endswith("/") or (tree / path).is_dir():
            path = normal(path + "/index.html")
        if not (tree / path).is_file():
            return "the published website does not have it"
        if fragment and path.endswith(".html") and fragment not in self.html(tree / path).ids:
            return f"{path} has no id {fragment}"
        return None

    def html(
        self,
        path: Path,  # A built page
    ) -> Ids:  # Its ids and links
        "Read a built page once."
        if path not in self.parsed:
            self.parsed[path] = parse_html(path)
        return self.parsed[path]

    def github(
        self,
        where: str,  # The page and the line of the link
        link: str,  # A link to github.com
    ) -> None:
        """With --github: the link answers 200, and each commit it names is in --repo."""
        if not self.online:
            return
        url = link.split("#")[0]
        hit = GITHUB.match(url)
        if hit and hit.group(3) and self.repo:
            ref = hit.group(4).removesuffix(".diff")
            for sha in ref.split("...") if hit.group(3) == "compare" else [ref]:
                if SHA.match(sha) and subprocess.run(["git", "-C", str(self.repo), "cat-file", "-e", f"{sha}^{{commit}}"],
                                                     capture_output=True, check=False).returncode:
                    self.problem(where, f"commit {sha[:12]} of {url} is not in {self.repo}")
        status = self.answer(url)
        if status != 200:
            self.problem(where, f"GitHub answers {status} for {url}")

    def answer(
        self,
        url: str,  # An address on GitHub
    ) -> int:  # The status of a HEAD request, after redirects; 0 when no answer came
        "Ask GitHub for an address once in a run, a pause apart, with a cache of the addresses that answered 200."
        if url in self.answers:
            return self.answers[url]
        cache = link_cache()
        known = read_cache(cache)
        if time.time() - known.get(url, 0) < CACHE_DAYS * 86400:
            self.answers[url] = 200
            return 200
        status = 0
        for attempt in range(4):
            wait = PAUSE - (time.monotonic() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.monotonic()
            status, retry = head(url)
            if status not in (429, 403, 0) or attempt == 3:
                break
            time.sleep(retry or 5 * (attempt + 1))
        self.answers[url] = status
        if status == 200:
            known[url] = time.time()
            write_cache(cache, known)
        return status


def head(
    url: str,  # An address
) -> tuple[int, float]:  # The status of a HEAD request, 0 if none came; and the seconds that Retry-After asks for, or 0
    "Send a HEAD request, and follow redirects."
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "walk-kit read_check"})
    try:
        with urllib.request.urlopen(request, timeout=30) as answer:
            return answer.status, 0
    except urllib.error.HTTPError as error:
        retry = error.headers.get("Retry-After", "") if error.headers else ""
        return error.code, float(retry) if retry.isdigit() else 0
    except (urllib.error.URLError, OSError):
        return 0, 0


def link_cache() -> Path:  # The file of the links that answered 200, with when
    "Find the cache of the links, in the user's cache folder."
    return render.cache_folder() / "links.json"


def read_cache(
    path: Path,  # The cache file
) -> dict[str, float]:  # Each address that answered 200, with when
    "Read the cache of the links; a missing or broken file is an empty cache."
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_cache(
    path: Path,  # The cache file
    known: dict[str, float],  # Each address that answered 200, with when
) -> None:
    """Write the cache of the links, without those older than the cache keeps."""
    now = time.time()
    keep = {url: when for url, when in known.items() if now - when < CACHE_DAYS * 86400}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(keep, indent=0, sort_keys=True), encoding="utf-8")
    except OSError:
        pass


def published_place(
    site: Path,  # The folder of a walk's pages on the website: site/, or site/ID/
) -> tuple[Path, str]:  # The website's folder, site/, which holds _smalldocs.yml; and the walk's folder in it: "" or "ID/"
    "Say which website a walk's pages are in, and where in it."
    if not (site / "_smalldocs.yml").is_file() and (site.parent / "_smalldocs.yml").is_file():
        return site.parent, f"{site.name}/"
    return site, ""


def other_walks(
    project: Path,  # The website's folder, site/
) -> list[str]:  # The folder of each other walk in it, as ID/
    "Find the folders of the other walks in a website: each folder of site/ with an index.qmd that render.py made."
    return sorted(f"{d.name}/" for d in project.iterdir() if d.is_dir() and (d / "index.qmd").is_file()
                  and render.MADE in (d / "index.qmd").read_text(encoding="utf-8", errors="replace"))


def owner(
    page: str | None,  # A page of the website, by its path from the top, or None for a warning of no page
    others: list[str],  # The folders of the other walks, as ID/
) -> str:  # The folder of the walk that has the page: "" for the first walk, or ID/
    "Say which walk a page of the website belongs to."
    return next((other for other in others if page and page.startswith(other)), "")


def warned_page(
    line: str,  # A line that smalldocs warned
) -> str | None:  # The page that it names, by its path in the website, or None
    "Find the page that a warning of smalldocs is about."
    found = re.match(r"^warning:\s*(.+?\.qmd):", line)
    return found.group(1) if found else None


def normal(
    path: str,  # A path in the built website, with . and .. in it perhaps
) -> str:  # The same path, without them
    "Resolve . and .. in a path of the website."
    parts: list[str] = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)


def main() -> int:  # The exit code: 1 if a page has a problem
    """Check each page to read."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("pages", type=Path, nargs="+", help="read.md pages, and pages of a website in read/")
    parser.add_argument("--repo", type=Path, help="the project: for the facts, and the commits that links name")
    parser.add_argument("--toc", type=Path, help="the class's toc.toml (default: toc.toml above walks/ and site/)")
    parser.add_argument("--facts", type=Path, help="the facts of one walk, for every page, in place of timewalk-export")
    parser.add_argument("--project-url", help="the project on GitHub, https://github.com/OWNER/NAME (default: the upstream and project of the justfile beside toc.toml)")
    parser.add_argument("--github", action="store_true", help="ask GitHub for every link to github.com")
    args = parser.parse_args()
    checker = Checker(args.repo.expanduser().resolve() if args.repo else None, args.toc.resolve() if args.toc else None, args.facts, args.github,
                      args.project_url)
    try:
        for page in args.pages:
            before = len(checker.problems)
            if not page.is_file():
                checker.problem(str(page), "no such page")
            else:
                checker.check_page(page.resolve())
            found = checker.problems[before:]
            print(f"{'FAIL' if found else 'ok  '} {page}" + (f" ({len(found)} problems)" if found else ""))
            for problem in found:
                print(f"  {problem}")
        before = len(checker.problems)
        checker.finish()
        found = checker.problems[before:]
        built = sum(1 for site in checker.sites.values() if site)
        websites = sum(1 for tree in checker.trees.values() if tree)
        print(f"{'FAIL' if found else 'ok  '} the pages of {built} walks, in {websites} website{'s' * (websites != 1)} built" +
              (f" ({len(found)} problems)" if found else ""))
        for problem in found:
            print(f"  {problem}")
    finally:
        checker.close()
    print(f"read_check: {len(args.pages)} pages, {len(checker.problems)} problems")
    return 1 if checker.problems else 0


if __name__ == "__main__":
    sys.exit(main())
