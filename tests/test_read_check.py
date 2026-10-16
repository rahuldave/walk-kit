"""read_check.py: a page to read, written by hand, passes, and each check fails when the page is broken on purpose.

    python3 -m unittest discover -s tests

The pages are of a small tutorial of two parts and three moves, with facts written by hand. The website tests build with
smalldocs through uvx. `TimewalkTest` renders the pages of timewalk-test's walks from a copy of it, and checks them all.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import read_check
import render
from test_review import TIMEWALK_TEST, copy_of_timewalk_test, git, missing

A, B, C = "a" * 40, "b" * 40, "c" * 40
URL = "https://github.com/o/demo"


def changed(
    path: str,  # The file
    status: str,  # added or modified
    diff: str,  # Its whole diff
    by: str | int = "patch",  # The do$ line that writes it, or "patch"
) -> dict:  # A file of a change, as the facts have it
    "Write a file of a change."
    return {"path": path, "old_path": None, "status": status, "added": diff.count("\n+"), "removed": 0, "binary": False, "diff": diff,
            "names": {"added": [], "removed": [], "changed": []}, "by": by, "patch": diff if by == "patch" else None}


def prose(
    text: str,  # The author's words
    mode: str = "shared",  # shared, do or watch
) -> dict:  # A part of prose
    "Write a part of the author's text."
    return {"kind": "prose", "mode": mode, "text": text}


def command(
    text: str,  # The command
    makes: bool,  # A do$ line, which makes the change
) -> dict:  # A part that is a command
    "Write a command of the notes."
    return {"kind": "command", "mode": "shared", "text": text, "makes": makes, "track": None, "writes": [], "take": None}


FACTS = {
    "format": 4, "walk": {"id": "w", "title": "Demo", "kind": "tutorial", "github": URL, "loose": []},
    "intro": [prose("We build demo, a file of words.")], "history": {}, "errors": [], "warnings": [], "observed": True,
    "stops": [
        {"name": "step-00", "number": "0", "title": "Where it starts", "tag": "step-00", "commit": A, "start": None, "own": None,
         "parts": [prose("The project has one word.")], "moves": [], "files": [changed("a.txt", "added", "@@ -0,0 +1 @@\n+one\n")]},
        {"name": "step-01", "number": "1", "title": "More words", "tag": "step-01", "commit": C, "start": A, "own": None,
         "parts": [prose("Two moves add words.")], "files": [], "moves": [
             {"name": "step-01.1", "number": "1.1", "title": "A second word", "commit": B, "parent": A,
              "files": [changed("a.txt", "modified", "@@ -1 +1,2 @@\n one\n+two\n")],
              "parts": [prose("A second word goes under the first."),
                        prose("Open `a.txt` in your editor, and add the word two on a line of its own at the end.", "do"),
                        {"kind": "patch", "mode": "shared", "path": "a.txt"}, command("cat a.txt", False)]},
             {"name": "step-01.2", "number": "1.2", "title": "A list of words", "commit": C, "parent": B,
              "files": [changed("uv.lock", "added", "@@ -0,0 +1 @@\n+lock\n", 0), changed("words.txt", "added", "@@ -0,0 +1,2 @@\n+one\n+two\n", 0)],
              "parts": [prose("A command writes the list, and a lock."), command("sort a.txt > words.txt", True)]}]}]}

PART_0 = f"""## 0 Where it starts

The project has one word.

### What changed

- <a id="step-00-a.txt"></a>`a.txt`: New, 1 line. [The file]({URL}/blob/{A}/a.txt).

<details><summary>The diff of <code>a.txt</code></summary>

```diff
@@ -0,0 +1 @@
+one
```

</details>

[The code of this part]({URL}/tree/{A}).
"""

MOVES = f"""## 1.1 A second word {{#step-01.1}}

A second word goes under the first.

A patch to [`a.txt`](#step-01.1-a.txt).

```bash
cat a.txt
```

### What changed

- <a id="step-01.1-a.txt"></a>`a.txt`: 1 line added. [The file]({URL}/blob/{B}/a.txt).

<details><summary>The diff of <code>a.txt</code></summary>

```diff
@@ -1 +1,2 @@
 one
+two
```

</details>

[This change on GitHub]({URL}/commit/{B}).

## 1.2 A list of words {{#step-01.2}}

A command writes the list, and a lock.

This change came from running `sort a.txt > words.txt`.

### What changed

- <a id="step-01.2-uv.lock"></a>`uv.lock`: New, 1 line. [The file]({URL}/blob/{C}/uv.lock).
- <a id="step-01.2-words.txt"></a>`words.txt`: New, 2 lines. [The file]({URL}/blob/{C}/words.txt).

<details><summary>The diff of <code>words.txt</code></summary>

```diff
@@ -0,0 +1,2 @@
+one
+two
```

</details>

[This change on GitHub]({URL}/commit/{C}).
"""


def deeper(
    text: str,  # Headings for a page of the website
) -> str:  # The same one level down, as the Markdown page has them, with the ids as <a id>
    "Turn the headings of a page of the website into those of the one Markdown page."
    out = []
    for line in text.split("\n"):
        if line.startswith("#"):
            name = line.split("{#")[1].rstrip("}") if "{#" in line else None
            line = "#" + line.split(" {#")[0]
            if name:
                out += [f'<a id="{name}"></a>', ""]
        out.append(line)
    return "\n".join(out)


READ_MD = ("# Demo\n\n**Read the tutorial.** [Build it yourself](build.md) is the other way to read it.\n\n"
           "We build demo, a file of words.\n\n" + PART_0 + "\n## 1 More words\n\nTwo moves add words.\n\n" + deeper(MOVES))
SITE_PAGES = {
    "_smalldocs.yml": ('project:\n  type: website\n  output-dir: _site\n  render: ["index.qmd", "read/*.qmd"]\n\nwebsite:\n  title: "Demo"\n'
                       '  sidebar:\n    contents:\n      - index.qmd\n      - text: "0 Where it starts"\n        href: read/step-00.qmd\n'
                       '      - text: "1.1 A second word"\n        href: read/step-01.qmd#step-01.1\n'),
    "index.qmd": '---\ntitle: "Demo"\n---\n\nWe build demo, a file of words.\n\n- [0 Where it starts](read/step-00.qmd)\n- [1 More words](read/step-01.qmd)\n',
    "read/step-00.qmd": '---\ntitle: "0 Where it starts"\n---\n\n' + PART_0.split("\n", 2)[2].replace("### What changed", "## What changed"),
    "read/step-01.qmd": '---\ntitle: "1 More words"\n---\n\nTwo moves add words.\n\n[The next part](step-00.qmd).\n\n' + MOVES,
}


class Case(unittest.TestCase):
    """A folder with the facts, a Markdown page to read, and a website."""

    def setUp(self) -> None:
        "Write the facts and the pages, and send the cache of links to the folder."
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        old = os.environ.get("XDG_CACHE_HOME")
        os.environ["XDG_CACHE_HOME"] = str(self.folder / "cache")
        self.addCleanup(lambda: os.environ.pop("XDG_CACHE_HOME") if old is None else os.environ.update(XDG_CACHE_HOME=old))
        self.facts = self.folder / "facts.json"
        self.facts.write_text(json.dumps(FACTS))
        self.page = self.folder / "md" / "walks" / "w" / "read.md"
        self.page.parent.mkdir(parents=True)
        self.page.write_text(READ_MD)
        (self.page.parent / "build.md").write_text("# Build it yourself\n")
        self.site = self.folder / "pages" / "site"
        for name, text in SITE_PAGES.items():
            (self.site / name).parent.mkdir(parents=True, exist_ok=True)
            (self.site / name).write_text(text)

    def check(
        self,
        page: Path,  # A page to read
        repo: Path | None = None,  # The project, for the commits of links
        online: bool = False,  # Ask GitHub, through read_check.head
    ) -> list[str]:  # The problems found
        "Check one page with the hand-written facts."
        checker = read_check.Checker(repo, None, self.facts, online)
        self.addCleanup(checker.close)
        checker.check_page(page)
        checker.finish()
        return checker.problems

    def broken(
        self,
        page: Path,  # A page to read
        old: str,  # Text of the page, found once
        new: str,  # What breaks it
        expected: str,  # Words of the problem that the check must report
        checked: Path | None = None,  # The page to check, when another file is broken; None for the page itself
    ) -> None:
        "Break a page in one place, and see the check fail with that problem."
        text = page.read_text()
        self.assertEqual(text.count(old), 1, old)
        page.write_text(text.replace(old, new))
        problems = self.check(checked or page)
        self.assertTrue(any(expected in problem for problem in problems), f"{expected!r} not in {problems}")
        page.write_text(text)


class Markdown(Case):
    """The Markdown page for GitHub: every check, on a page that has no website beside it."""

    def test_the_page_passes(self) -> None:
        self.assertEqual(self.check(self.page), [])

    def test_what_render_writes_passes(self) -> None:
        "render.py's Read the tutorial of the same facts passes too, and its Build it yourself fails as a page to read."
        files = render.markdown_files(FACTS)
        self.page.write_text(files["read.md"])
        self.assertEqual(self.check(self.page), [])
        self.page.write_text(files["build.md"])
        problems = self.check(self.page)
        for words in ("a `git check`", "takes the files of a commit", "Get the project", "Check your files against this", "in a block of shell"):
            self.assertTrue(any(words in problem for problem in problems), f"{words!r} not in {problems}")

    def test_nothing_to_run(self) -> None:
        page = self.page
        self.broken(page, "```bash\ncat a.txt\n```", "```bash\ncat a.txt\ngit check bbbbbbb\n```", "a `git check`")
        self.broken(page, "```bash\ncat a.txt\n```", f"```bash\ncurl -fsSL {URL}/commit/{B}.diff | git apply --include=a.txt\n```",
                    "a patch to apply")
        self.broken(page, "```bash\ncat a.txt\n```", "```sh\ngit restore --source aaaaaaa --staged -- :/ && git restore --source "
                    "bbbbbbb --staged --worktree -- :/\n```", "takes the files of a commit")
        self.broken(page, "Two moves add words.", "Two moves add words.\n\n## Get the project", "Get the project")
        self.broken(page, "Two moves add words.", "Check your files against this move.", "text of Build it yourself")
        self.broken(page, "Two moves add words.", "Then change `a.txt` as its patch shows.", "text of Build it yourself")
        self.broken(page, "<details><summary>The diff of <code>words.txt", "<details open><summary>The patch to <code>words.txt",
                    "text of Build it yourself")

    def test_a_command_that_made_the_change_is_to_read(self) -> None:
        self.broken(self.page, "This change came from running `sort a.txt > words.txt`.", "```bash\nsort a.txt > words.txt\n```",
                    "is not shown as")
        self.broken(self.page, "This change came from running `sort a.txt > words.txt`.",
                    "This change came from running `sort a.txt > words.txt`.\n\n```bash\nsort a.txt > words.txt\n```", "in a block of shell")
        self.broken(self.page, "running `sort a.txt > words.txt`.", "running `sort a.txt`.", "is not shown as")

    def test_the_walk_preamble_is_left_out(self) -> None:
        "The notes of a walk repository start with the walk preamble, and the pages, made from the class's notes, do not have it."
        intro = read_check.PREAMBLE + "\n\nWe build demo, a file of words."
        self.facts.write_text(json.dumps({**FACTS, "intro": [prose(intro)]}))
        self.assertEqual(self.check(self.page), [])
        self.broken(self.page, "We build demo, a file of words.", "We build demo.", "the intro's text is missing")

    def test_the_text_of_build_it_yourself_is_not_there(self) -> None:
        self.broken(self.page, "A second word goes under the first.",
                    "A second word goes under the first.\n\nOpen `a.txt` in your editor, and add the word two on a line of its own at the end.",
                    "text of Build it yourself")

    def test_every_move_in_order_with_its_title(self) -> None:
        self.broken(self.page, "### 1.2 A list of words", "### 1.2 A list of names", "step-01.2 '1.2 A list of words' is missing")
        self.broken(self.page, "## 0 Where it starts", "## Where it starts", "step-00 '0 Where it starts' is missing")
        self.broken(self.page, "### 1.1 A second word", "#### 1.1 A second word", "step-01.1 '1.1 A second word' is missing")
        text = self.page.read_text()
        one, two = text.index('<a id="step-01.1">'), text.index('<a id="step-01.2">')
        self.page.write_text(text[:one] + text[two:] + "\n" + text[one:two])
        self.assertTrue(any("out of order" in problem for problem in self.check(self.page)))

    def test_the_text_of_each_move(self) -> None:
        self.broken(self.page, "A second word goes under the first.", "A second word goes under it.", "the text is missing, or changed")
        self.broken(self.page, "We build demo, a file of words.", "We build demo.", "the intro's text is missing")
        self.broken(self.page, "A patch to [`a.txt`](#step-01.1-a.txt).", "", "no \"A patch to `a.txt`\"")

    def test_every_file_and_its_diff(self) -> None:
        self.broken(self.page, f"- <a id=\"step-01.2-uv.lock\"></a>`uv.lock`: New, 1 line. [The file]({URL}/blob/{C}/uv.lock).\n", "",
                    "What changed does not list uv.lock")
        self.broken(self.page, " one\n+two\n```", " one\n+three\n```", "the diff of a.txt differs from the commit's diff")
        self.broken(self.page, "<summary>The diff of <code>words.txt</code></summary>", "<summary>The diff of <code>other.txt</code></summary>",
                    "a diff of other.txt, which the change does not have")
        text = self.page.read_text()
        start = text.index("<details><summary>The diff of <code>words.txt")
        self.page.write_text(text[:start] + text[text.index("</details>", start) + len("</details>"):])
        self.assertTrue(any("no diff of words.txt" in problem for problem in self.check(self.page)))
        self.page.write_text(text)
        self.broken(self.page, "\n#### What changed\n\n- <a id=\"step-01.2", "\n- <a id=\"step-01.2", "no heading What changed")

    def test_the_link_to_the_change(self) -> None:
        self.broken(self.page, f"[This change on GitHub]({URL}/commit/{C})", f"[This change on GitHub]({URL}/commit/{B})",
                    f"no link [This change on GitHub]({URL}/commit/{C})")
        self.broken(self.page, f"[The code of this part]({URL}/tree/{A})", f"[The code of this part]({URL}/tree/{B})", "no link [The code of this part]")

    def test_links_and_ids(self) -> None:
        self.broken(self.page, "(#step-01.1-a.txt)", "(#step-01.1-a-txt)", "a link to #step-01.1-a-txt, which the page does not have")
        self.broken(self.page, "(build.md)", "(build2.md)", "a link to build2.md, which does not exist")
        self.broken(self.page, "(build.md)", "(build.md#get-the-project)", "build.md has no such id")
        self.broken(self.page, '<a id="step-01.2"></a>', '<a id="step-01.1"></a>', "the id 'step-01.1' is given twice")
        (self.page.parent / "build.md").write_text("# Build it yourself\n\n## Get the project\n")
        self.page.write_text(READ_MD.replace("(build.md)", "(build.md#get-the-project)"))   # the id that GitHub gives a heading
        self.assertEqual(self.check(self.page), [])

    def test_a_link_to_a_heading_passes(self) -> None:
        "GitHub gives each heading an id: lower case, a hyphen for each space, without the dots."
        self.page.write_text(READ_MD.replace("Two moves add words.", "Two moves add words. See [the first part](#0-where-it-starts) and [its "
                                             "list](#what-changed), and [the second list](#what-changed-1)."))
        self.assertEqual(self.check(self.page), [])
        self.broken(self.page, "(#what-changed-1)", "(#what-changed-9)", "#what-changed-9")


class Site(Case):
    """A page of the website: its links in the built site, and the build itself."""

    def test_the_pages_pass(self) -> None:
        for page in ("read/step-00.qmd", "read/step-01.qmd"):
            self.assertEqual(self.check(self.site / page), [], page)

    def test_what_render_writes_passes(self) -> None:
        shutil.rmtree(self.site)
        for name, text in render.site_files(FACTS).items():
            (self.site / name).parent.mkdir(parents=True, exist_ok=True)
            (self.site / name).write_text(text)
        for page in sorted((self.site / "read").glob("*.qmd")):
            self.assertEqual(self.check(page), [], page)

    def test_the_part_and_its_moves(self) -> None:
        page = self.site / "read" / "step-01.qmd"
        self.broken(page, 'title: "1 More words"', 'title: "1 More"', "the title is '1 More'")
        self.broken(page, "## 1.1 A second word {#step-01.1}", "### 1.1 A second word {#step-01.1}", "step-01.1 '1.1 A second word' is missing")
        self.broken(page, " one\n+two\n```", " one\n+two\n+three\n```", "the diff of a.txt differs")
        (self.site / "read" / "step-09.qmd").write_text('---\ntitle: "9 Nine"\n---\n\nNine.\n')
        self.assertTrue(any("no part of walk w" in problem for problem in self.check(self.site / "read" / "step-09.qmd")))

    def test_a_part_without_a_page(self) -> None:
        (self.site / "read" / "step-00.qmd").unlink()
        problems = self.check(self.site / "read" / "step-01.qmd")
        self.assertTrue(any("no page read/step-00.qmd for step-00" in problem for problem in problems), problems)

    def test_links_in_the_built_site(self) -> None:
        page = self.site / "read" / "step-01.qmd"
        self.broken(page, "[The next part](step-00.qmd)", "[The next part](step-00.qmd#nowhere)", "read/step-00.html has no id nowhere")
        self.broken(page, "[The next part](step-00.qmd)", "[The next part](step-07.qmd)", "the published website does not have it")
        self.broken(page, "(#step-01.1-a.txt)", "(#step-01.1-a-txt)", "read/step-01.html has no id step-01.1-a-txt")

    def test_the_sidebar(self) -> None:
        "A page that the sidebar lists, and a link of the sidebar, must be built: smalldocs warns, and the built page has no such id."
        config = self.site / "_smalldocs.yml"
        page = self.site / "read" / "step-01.qmd"
        self.broken(config, "href: read/step-01.qmd#step-01.1", "href: read/step-01.qmd#step-01.7", "has no id step-01.7", page)
        self.broken(config, "href: read/step-00.qmd", "href: read/step-05.qmd", "lists read/step-05.qmd, and smalldocs did not build it", page)
        self.assertEqual(self.check(page), [])

    def test_the_sites_put_together(self) -> None:
        "Each other walk's pages are at ID/ in the one website: a link between them resolves there, and a link to a walk without pages does not."
        other = self.site / "x"
        (other / "read").mkdir(parents=True)
        config = self.site / "_smalldocs.yml"
        config.write_text(config.read_text().replace("render: [", 'render: ["x/index.qmd", ', 1))
        (other / "index.qmd").write_text('---\ntitle: "X"\n---\n\nThe [first walk](../) lists them all.\n')
        index = self.site / "index.qmd"
        index.write_text(index.read_text() + "\nThe other walk: [X](x/).\n")

        def check() -> list[str]:
            checker = read_check.Checker(None, None, self.facts, False)
            self.addCleanup(checker.close)
            checker.check_page(self.site / "read" / "step-01.qmd")
            checker.site(other, None)
            checker.finish()
            return checker.problems

        self.assertEqual(check(), [])
        index.write_text(index.read_text() + "\nAnd [Y](y/).\n")
        problems = check()
        self.assertTrue(any("links to y: the published website does not have it" in problem for problem in problems), problems)

    def test_a_site_that_does_not_build(self) -> None:
        self.broken(self.site / "read" / "step-00.qmd", 'title: "0 Where it starts"', 'title: "0 Where it starts', "smalldocs failed")


class GitHub(Case):
    """With --github, each link to github.com answers 200, and each commit that it names is in the project."""

    def setUp(self) -> None:
        "Make a project with one commit, and a GitHub that answers from a table."
        super().setUp()
        self.repo = self.folder / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "a.txt").write_text("one\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "one")
        self.sha = git(self.repo, "rev-parse", "HEAD")
        self.asked: list[str] = []
        self.status: dict[str, int] = {}
        saved = read_check.head, read_check.PAUSE
        self.addCleanup(lambda: setattr(read_check, "head", saved[0]) or setattr(read_check, "PAUSE", saved[1]))
        read_check.PAUSE = 0
        read_check.head = lambda url: (self.asked.append(url), (self.status.get(url, 200), 0))[1]
        self.page.write_text(f"# Links\n\n[The file]({URL}/blob/{self.sha}/a.txt). [The change]({URL}/commit/{self.sha}).\n"
                             f"[Again]({URL}/blob/{self.sha}/a.txt).\n")
        self.facts.write_text(json.dumps({**FACTS, "intro": [], "stops": []}))

    def test_links_that_answer(self) -> None:
        self.assertEqual(self.check(self.page, self.repo, online=True), [])
        self.assertEqual(sorted(self.asked), [f"{URL}/blob/{self.sha}/a.txt", f"{URL}/commit/{self.sha}"])   # each address once
        self.asked.clear()
        self.assertEqual(self.check(self.page, self.repo, online=True), [])
        self.assertEqual(self.asked, [], "a link that answered 200 is in the cache")

    def test_a_link_that_does_not_answer(self) -> None:
        self.status[f"{URL}/commit/{self.sha}"] = 404
        problems = self.check(self.page, self.repo, online=True)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn(f"GitHub answers 404 for {URL}/commit/{self.sha}", problems[0])

    def test_a_commit_that_the_project_does_not_have(self) -> None:
        self.page.write_text(f"# Links\n\n[The change]({URL}/compare/{self.sha}...{'d' * 40}).\n")
        problems = self.check(self.page, self.repo, online=True)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn(f"commit {'d' * 12} of", problems[0])

    def test_offline_asks_nothing(self) -> None:
        self.status[f"{URL}/commit/{self.sha}"] = 404
        self.assertEqual(self.check(self.page, self.repo), [])
        self.assertEqual(self.asked, [])


@unittest.skipIf(missing(), missing())
class TimewalkTest(unittest.TestCase):
    """Every page to read of timewalk-test's walks, rendered from a copy of it, passes."""

    def test_every_page_to_read(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            folder = copy_of_timewalk_test(TIMEWALK_TEST, Path(scratch))
            pages = Path(scratch) / "pages"
            done = subprocess.run([sys.executable, str(KIT / "scripts" / "render.py"), "--class", str(folder), "--repo", str(folder / "repo"),
                                   "--github", "https://github.com/rahuldave/tally", "--pages", str(pages)], capture_output=True, text=True, check=False)
            self.assertEqual(done.returncode, 0, done.stderr)
            read = sorted(pages.glob("walks/*/read.md")) + sorted(pages.glob("site/read/*.qmd")) + sorted(pages.glob("site/*/read/*.qmd"))
            self.assertGreater(len(read), 10)
            done = subprocess.run([sys.executable, str(KIT / "scripts" / "read_check.py"), *map(str, read), "--repo", str(folder / "repo"),
                                   "--toc", str(folder / "toc.toml")], capture_output=True, text=True, check=False)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertIn(f"read_check: {len(read)} pages, 0 problems", done.stdout)



class Address(unittest.TestCase):
    "The project's address on GitHub is given or read from the class's justfile, never taken from a link in a page."

    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        (self.folder / "toc.toml").write_text('[[walk]]\nid = "w"\nkind = "tutorial"\nnotes = "notes.md"\n')
        (self.folder / "walks" / "w").mkdir(parents=True)
        self.page = self.folder / "walks" / "w" / "read.md"
        # the first link is another repository, as wikiapp's pages open with a link to the original project
        self.page.write_text("Made from [the original](https://github.com/someone/original).\n\n"
                             "[A file](https://github.com/rahuldave/demo/blob/abc/f.txt)\n")
        self.asked: list[str] = []
        saved = render.export
        self.addCleanup(lambda: setattr(render, "export", saved))
        render.export = lambda repo, toc, ident, address, scratch: self.asked.append(address) or {"walk": {}, "stops": []}

    def facts(self, given: str | None = None) -> list[str]:
        "Ask the checker for the facts of the page's walk, and give the problems."
        checker = read_check.Checker(self.folder, None, None, False, given)
        self.addCleanup(checker.close)
        checker.facts_for(self.page.resolve(), read_check.Text(self.page.resolve()))
        return checker.problems

    def test_from_the_justfile(self) -> None:
        (self.folder / "justfile").write_text('project := "demo"\nupstream := "rahuldave"\n')
        self.assertEqual(self.facts(), [])
        self.assertEqual(self.asked, ["https://github.com/rahuldave/demo"])

    def test_given(self) -> None:
        self.assertEqual(self.facts("https://github.com/rahuldave/demo.git"), [])
        self.assertEqual(self.asked, ["https://github.com/rahuldave/demo"])

    def test_never_guessed(self) -> None:
        problems = self.facts()
        self.assertEqual(self.asked, [], "no export with a guessed address")
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("upstream :=", problems[0])

    def test_one_function_for_every_script(self) -> None:
        "No script of walk-kit takes an address from a link in a page or from a git remote."
        for script in (KIT / "scripts").glob("*.py"):
            text = script.read_text()
            self.assertNotIn("get-url", text, script.name)
            self.assertNotIn("links_of(text) for hit in [GITHUB.match", text, script.name)


if __name__ == "__main__":
    unittest.main()
