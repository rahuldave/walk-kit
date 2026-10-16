"""Tests of render.py's commands for Build it yourself: git check, a pyproject.toml set as data, and the patch of a renamed file.

    python3 -m unittest discover -s tests

Each test makes a small git repository in a temporary folder. The tests of pyproject.toml and uv.lock need uv.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import render

ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
       "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
PYPROJECT = '[project]\nname = "demo"\nversion = "0.1.0"\nrequires-python = ">=3.11"\ndependencies = []\n'


def sh(
    cwd: Path,  # Where to run it
    command: str,  # A line of shell
    check: bool = True,  # Fail the test if it fails
) -> subprocess.CompletedProcess:  # What it printed, and its exit code
    "Run a line of shell, as a learner types it."
    done = subprocess.run(["sh", "-c", command], cwd=cwd, capture_output=True, text=True, env=ENV, check=False)
    if check and done.returncode:
        raise AssertionError(f"{command} failed: {done.stdout}{done.stderr}")
    return done


def commit(
    repo: Path,  # The repository
    files: dict,  # Each file to write by its path, or None to delete it
    subject: str,  # The commit's subject
) -> str:  # The new commit
    "Write the files and commit them all."
    for path, text in files.items():
        target = repo / path
        if text is None:
            target.unlink()
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
    sh(repo, "git add -A")
    sh(repo, f"git commit -qm '{subject}'")
    return sh(repo, "git rev-parse HEAD").stdout.strip()


def facts_of(
    loose: list[str],  # The walk's loose
    shas: list[str] = (),  # The commits of its moves, in one stop
) -> dict:  # Facts with what these tests need
    "Make the facts of a tutorial of one stop."
    moves = [{"commit": sha, "name": f"step-01.{n}", "parts": []} for n, sha in enumerate(shas, 1)]
    return {"walk": {"kind": "tutorial", "loose": loose, "github": "https://github.com/o/demo"},
            "stops": [{"commit": shas[-1] if shas else "", "start": None, "moves": moves}]}


class Case(unittest.TestCase):
    "A temporary folder, with a repository of the project in it."

    def setUp(self) -> None:
        "Make the folder and the repository."
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.repo = self.folder / "repo"
        self.repo.mkdir()
        sh(self.repo, "git init -q -b main")

    def learner(
        self,
        facts: dict,  # The facts, for the git check alias
        start: str,  # The commit where the learner starts
    ) -> Path:  # The learner's clone, on mine, with git check
        "Clone the project as Get the project says, and add git check."
        sh(self.folder, f"git clone -q {self.repo} work")
        work = self.folder / "work"
        sh(work, f"git switch -qc mine {start}")
        for line in render.check_lines(facts):
            sh(work, line)
        return work


class GitCheck(Case):
    "git check compares the learner's files with a commit, and leaves git's index alone."

    def test_index_stays(self) -> None:
        "After a check, git diff still shows the learner's edit, and a new file is still untracked, but the check counts both."
        start = commit(self.repo, {"a.txt": "a\n", "b.txt": "b\n"}, "start")
        work = self.learner(facts_of([]), start)
        (work / "a.txt").write_text("a\nmore\n")
        (work / "new.txt").write_text("new\n")
        found = sh(work, f"git check {start}").stdout
        self.assertIn("a.txt", found)
        self.assertIn("new.txt", found)
        self.assertEqual(sh(work, "git diff --name-only").stdout, "a.txt\n")
        self.assertEqual(sh(work, "git diff --cached --name-only").stdout, "")
        self.assertEqual(sh(work, "git status --porcelain").stdout, " M a.txt\n?? new.txt\n")

    def test_match(self) -> None:
        "Files that equal the commit's print nothing, with an ignored file and a deleted file."
        start = commit(self.repo, {"a.txt": "a\n", "gone.txt": "g\n", ".gitignore": "out/\n"}, "start")
        sha = commit(self.repo, {"a.txt": "a\nb\n", "gone.txt": None, "c.txt": "c\n"}, "move")
        work = self.learner(facts_of([]), start)
        (work / "a.txt").write_text("a\nb\n")
        (work / "c.txt").write_text("c\n")
        (work / "gone.txt").unlink()
        (work / "out").mkdir()
        (work / "out" / "x").write_text("ignored\n")
        self.assertEqual(sh(work, f"git check {sha}").stdout, "")
        self.assertIn("c.txt", sh(work, f"git check {start}").stdout)

    def test_staged_stays(self) -> None:
        "What the learner staged stays staged, and nothing else is staged, so git rm meets the index that the learner made."
        start = commit(self.repo, {"a.txt": "a\n", "b.txt": "b\n"}, "start")
        work = self.learner(facts_of([]), start)
        (work / "a.txt").write_text("staged\n")
        sh(work, "git add a.txt")
        (work / "a.txt").write_text("staged, then changed\n")
        (work / "b.txt").write_text("changed\n")
        before = sh(work, "git ls-files -s").stdout
        sh(work, f"git check {start}")
        self.assertEqual(sh(work, "git ls-files -s").stdout, before)
        self.assertIn("has local modifications", sh(work, "git rm b.txt", check=False).stderr)   # git's own rule, not the check's

    def test_loose(self) -> None:
        "With loose, another version of a package in pyproject.toml matches, and a missing uv.lock does not."
        if not shutil.which("uv"):
            self.skipTest("uv is not installed")
        start = commit(self.repo, {"pyproject.toml": PYPROJECT.replace("[]", '[\n    "six>=1.0",\n]'), "uv.lock": "x\n"}, "start")
        work = self.learner(facts_of(["pyproject.toml", "uv.lock"]), start)
        (work / "pyproject.toml").write_text(PYPROJECT.replace("[]", '[\n    "six>=1.16",\n]'))
        (work / "uv.lock").unlink()
        found = sh(work, f"git check {start}", check=False)
        self.assertIn("deleted file mode", found.stdout)
        self.assertIn("uv.lock", found.stdout)
        self.assertNotIn("six", found.stdout)
        self.assertEqual(sh(work, "git diff --cached --name-only").stdout, "")


class Rename(Case):
    "The patch of a renamed file renames it, by the file's new path, which git apply matches."

    def test_rename_by_patch(self) -> None:
        "patch$ on the old path gives git apply --include with the new path, and git check passes after it."
        body = "".join(f"line {n}\n" for n in range(20))
        start = commit(self.repo, {"tests/test_old.py": body, "other.py": "x\n"}, "start")
        sh(self.repo, "git mv tests/test_old.py tests/test_new.py")
        sha = commit(self.repo, {"tests/test_new.py": body + "line 20\n", "other.py": "y\n"}, "rename")
        files = [{"path": "other.py", "old_path": None, "status": "modified", "by": "patch", "binary": False},
                 {"path": "tests/test_new.py", "old_path": "tests/test_old.py", "status": "renamed", "by": "patch", "binary": False}]
        page = render.Page(facts_of([]), "do", False)
        patches = [{"kind": "patch", "mode": "shared", "path": path} for path in ("tests/test_old.py", "tests/test_new.py")]   # as timewalk-check asks
        page.parts(patches, sha, files, "step-01.1")
        lines = [line for line in page.lines if line.startswith("curl")]
        self.assertEqual(len(lines), 1, "the two patch$ lines of a rename give one patch")
        line = lines[0]
        self.assertTrue(line.endswith("git apply --include=tests/test_new.py"), line)
        self.assertIn("renames `tests/test_old.py`", "\n".join(page.lines))
        work = self.learner(facts_of([]), start)
        diff = re.sub(r"curl -fsSL \S+", f"git -C {self.repo} diff {start} {sha}", line)   # GitHub's diff, from the local repository
        sh(work, diff)
        sh(work, f"git -C {self.repo} diff {start} {sha} | git apply --include=other.py")
        self.assertEqual(sh(work, f"git check {sha}").stdout, "")

    def test_old_include_skips(self) -> None:
        "git apply matches --include against the new path: the old path skips the patch and exits 0, as the bug did."
        start = commit(self.repo, {"old.txt": "".join(f"{n}\n" for n in range(20))}, "start")
        sh(self.repo, "git mv old.txt new.txt")
        sha = commit(self.repo, {}, "rename")
        sh(self.repo, f"git checkout -q {start}")
        done = sh(self.repo, f"git diff {start} {sha} | git apply -v --include=old.txt")
        self.assertIn("Skipped patch", done.stderr)
        self.assertTrue((self.repo / "old.txt").exists())



class FirstPart(Case):
    "A part with no move has a check too, the first part as well: it says that the learner's clone is right."

    def test_first_part_checks(self) -> None:
        "The first part, with no move, ends with git check of its commit, and the check passes in a clone made as the page says."
        sha = commit(self.repo, {"a.txt": "a\n"}, "start")
        facts = facts_of([])
        stop = {"name": "step-00", "number": "0", "title": "Where it starts", "start": None, "commit": sha, "parts": [], "files": [],
                "moves": []}
        facts["stops"] = [stop]
        lines = render.stop_page(facts, stop, 1, "do", True)
        self.assertIn(f"git check {sha[:12]}", lines)
        self.assertEqual(sh(self.learner(facts, sha), f"git check {sha[:12]}").stdout, "")
        self.assertNotIn(f"git check {sha[:12]}", render.stop_page(facts, stop, 1, "watch", True))


class OneMovePart(unittest.TestCase):
    "A small walk can select one move as a part, so the part and its move have one name."

    def test_one_id(self) -> None:
        "The Markdown page gives the id once: the part's, and the move's heading follows it, so a link finds that part."
        move = {"name": "step-05.1", "number": "5.1", "title": "Top words", "commit": "b" * 40, "parts": [], "files": []}
        stop = {"name": "step-05.1", "number": "5.1", "title": "Top words", "start": "a" * 40, "commit": "b" * 40, "parts": [],
                "files": [], "moves": [move]}
        facts = {"walk": {"kind": "narrative", "github": "https://github.com/o/demo"}, "stops": [stop], "history": {}}
        for mode in ("watch", "do"):
            text = "\n".join(render.stop_page(facts, stop, 1, mode, False))
            self.assertEqual(text.count('<a id="step-05.1"></a>'), 1, text)
            self.assertIn("### 5.1 Top words", text)



class CheckAgainst(unittest.TestCase):
    "Only Build it yourself tells the reader to check files against What changed: a reader of Read the tutorial makes none."

    def test_read_pages_do_not_say_it(self) -> None:
        "Read the tutorial and a narrative's front page leave the sentence out; Build it yourself and a tutorial's front page have it."
        for kind in ("tutorial", "narrative"):
            facts = {"walk": {"id": "w", "title": "Demo", "kind": kind, "github": "https://github.com/o/demo", "loose": []}, "intro": [],
                     "stops": [], "history": {}}
            pages = render.markdown_files(facts)
            self.assertNotIn(render.CHECK_AGAINST, pages["read.md"])
            self.assertEqual(render.CHECK_AGAINST in pages.get("build.md", ""), kind == "tutorial")
            self.assertEqual(render.CHECK_AGAINST in render.site_files(facts)["index.qmd"], kind == "tutorial")


class IndexCommands(unittest.TestCase):
    "A git rm or git mv on a page fails for a student who never commits when git's index does not hold the file, so the check of a class names it."

    def facts(self, *texts: str, before: list[dict] = (), writes: list[str] | None = None) -> dict:
        "Facts of a walk: a move that changes the files before, then a move with these commands, the first a do$ line that writes writes."
        parts = [{"kind": "command", "text": text, "makes": not n, "mode": "shared", "writes": writes if not n else None}
                 for n, text in enumerate(texts)]
        moves = [{"name": "step-01.1", "parts": [], "files": list(before)}, {"name": "step-01.2", "parts": parts, "files": []}]
        return {"walk": {"kind": "tutorial", "loose": []},
                "stops": [{"name": "step-01", "start": "a" * 40, "commit": "b" * 40, "parts": [], "files": [], "moves": moves}]}

    def file(self, path: str, status: str, old: str | None = None) -> dict:
        "A file of a change."
        return {"path": path, "status": status, "old_path": old}

    def test_untouched_files_pass(self) -> None:
        "git rm and git mv of files that the walk has not changed work for a student: the repro's git mv of a test from before the walk."
        self.assertEqual(render.index_commands(self.facts("git mv tests/test_empty.py tests/test_blank.py", "git rm old.py", "git rm -r build")), [])

    def test_rm_of_a_changed_file(self) -> None:
        "git rm of a file that an earlier move added or changed is named, with the reason."
        for status in ("added", "modified"):
            found = render.index_commands(self.facts("git rm app.py", before=[self.file("app.py", status)]))
            self.assertEqual(len(found), 1, found)
            self.assertIn("`app.py`", found[0])
            self.assertIn("Write `rm`", found[0])

    def test_rm_force(self) -> None:
        "git rm -f of a file that git tracks works, and of a file that the walk added does not."
        modified = self.facts("git rm -f app.py", before=[self.file("app.py", "modified")])
        self.assertEqual(render.index_commands(modified), [])
        self.assertEqual(len(render.index_commands(self.facts("git rm -qf app.py", before=[self.file("app.py", "added")]))), 1)

    def test_mv(self) -> None:
        "git mv of a file that the walk added is named; of a file that it changed, or renamed from a file the walk did not add, passes too."
        self.assertEqual(len(render.index_commands(self.facts("git mv -v new.py b.py", before=[self.file("new.py", "added")]))), 1)
        self.assertEqual(render.index_commands(self.facts("git mv app.py b.py", before=[self.file("app.py", "modified")])), [])
        self.assertEqual(render.index_commands(self.facts("git mv -- app.py old.py b/", before=[self.file("x.py", "added")])), [])
        self.assertEqual(len(render.index_commands(self.facts("git mv b.py c.py", before=[self.file("b.py", "renamed", "a.py")]))), 1)

    def test_folder_and_glob(self) -> None:
        "A folder or a glob is named when it holds a file that fails, and the problem says which file."
        before = [self.file("src/app.py", "modified")]
        for text in ("git rm -r src", "git rm -r src/", "uv lock && git rm 'src/*.py'", "git rm -r ."):
            found = render.index_commands(self.facts(text, before=before))
            self.assertEqual(len(found), 1, text)
            self.assertIn("`src/app.py`", found[0])
            self.assertIn("names it", found[0])
        self.assertEqual(render.index_commands(self.facts("git rm -r lib 'docs/*.md'", before=before)), [])

    def test_earlier_in_the_move(self) -> None:
        "A do$ line earlier in the move that writes a file: git rm of it is named, and git mv of it too, as git does not track it."
        self.assertEqual(len(render.index_commands(self.facts("make", "git rm out.txt", writes=["out.txt"]))), 1)
        self.assertEqual(len(render.index_commands(self.facts("make", "git mv out.txt o.txt", writes=["out.txt"]))), 1)

    def test_others_pass(self) -> None:
        "rm, mv, git restore and a word that only starts like it are not named."
        before = [self.file("old.py", "added"), self.file("a.py", "added")]
        self.assertEqual(render.index_commands(self.facts("rm old.py", "mv a.py b.py", "git restore x", "git rmdir", "echo git-rm", before=before)), [])

    def test_check_class_counts_it(self) -> None:
        "just check, through check_class, counts a git mv of a file that the walk added as a problem."
        facts = self.facts("git mv a.py b.py", before=[self.file("a.py", "added")])
        saved = render.export, render.toml_edits, render.page_walks, render.source_gaps, render.markdown_files, render.our_words
        self.addCleanup(lambda: setattr(render, "export", saved[0]) or setattr(render, "toml_edits", saved[1])
                        or setattr(render, "page_walks", saved[2]) or setattr(render, "source_gaps", saved[3])
                        or setattr(render, "markdown_files", saved[4]) or setattr(render, "our_words", saved[5]))
        render.export = lambda *args: facts
        render.toml_edits = lambda *args: {}
        render.page_walks = lambda toc: [{"id": "w"}]
        render.source_gaps = render.our_words = lambda facts: []
        render.markdown_files = lambda facts: {}
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(render.check_class(Path(folder), Path(folder), "https://github.com/o/demo"), 1)

    def test_a_git_mv_fails_for_the_student(self) -> None:
        "The reason: after git check, git mv of a file that the student made is refused; of a file of the project, changed or not, it works."
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            sh(work, "git init -q -b main && echo a > f && echo b > g && echo c > h && git add f g h && git commit -qm a")
            for line in render.check_lines({"walk": {"loose": []}}):
                sh(work, line)
            sh(work, "echo n > new.py && echo more >> g && git check HEAD > /dev/null")
            self.assertNotEqual(sh(work, "git mv new.py other.py", check=False).returncode, 0)
            self.assertEqual(sh(work, "mv new.py other.py").returncode, 0)
            self.assertEqual(sh(work, "git mv f f2 && git mv g g2").returncode, 0)
            self.assertNotEqual(sh(work, "git rm -q g2", check=False).returncode, 0)
            self.assertEqual(sh(work, "git rm -q h").returncode, 0)


class AfterPatch(Case):
    "A move whose do$ line writes a file that the author then changes more: Build it yourself gives the command for the rest."

    def facts(self, path: str, base: str, patch: str) -> tuple[dict, dict]:
        "Facts of one move: a do$ line, then patch$ PATH."
        parts = [{"kind": "command", "text": f"printf x >> '{path}'", "makes": True, "mode": "shared", "track": "", "writes": [path]},
                 {"kind": "patch", "mode": "shared", "path": path}]
        found = {"path": path, "old_path": None, "status": "modified", "added": 2, "removed": 0, "binary": False, "diff": patch,
                 "names": {"added": [], "removed": [], "changed": []}, "by": 0, "patch": patch}
        move = {"name": "step-01.1", "number": "1.1", "title": "More", "commit": "c" * 40, "parts": parts, "files": [found]}
        stop = {"name": "step-01", "number": "1", "title": "One", "start": base, "commit": "c" * 40, "parts": [], "files": [found], "moves": [move]}
        return {"walk": {"kind": "tutorial", "loose": [], "github": "https://github.com/o/demo"}, "observed": True, "stops": [stop],
                "history": {}}, stop

    def test_the_command_applies(self) -> None:
        "follow reads the git apply and its here-document as one command, and it applies to the file as the student's do$ line left it."
        import follow

        path = "conf/my file.toml"
        (self.repo / "conf").mkdir()
        (self.repo / path).write_text('[group]\ndev = [\n    "ruff>=0.18.0",\n]\n')   # the student's uv add wrote a newer version
        patch = '@@ -2,3 +2,7 @@\n dev = [\n     "ruff>=0.17.0",\n ]\n+\n+```\n+ PATCH\n+line-length = 100\n'
        facts, stop = self.facts(path, "a" * 40, patch)
        page = "\n".join(render.stop_page(facts, stop, 1, "do", False))
        self.assertNotIn("as its patch shows", page)
        commands = [c for block in follow.blocks_of(page) for c in block.commands if c.startswith("git apply")]
        self.assertEqual(len(commands), 1, page)
        sh(self.repo, commands[0])
        self.assertEqual((self.repo / path).read_text(), '[group]\ndev = [\n    "ruff>=0.18.0",\n]\n\n```\n PATCH\nline-length = 100\n')

    def test_watch_shows_the_diff(self) -> None:
        "Read the tutorial says a patch, and gives no command."
        facts, stop = self.facts("pyproject.toml", "a" * 40, "@@ -1 +1,2 @@\n a\n+b\n")
        page = "\n".join(render.stop_page(facts, stop, 1, "watch", False))
        self.assertIn("A patch to", page)
        self.assertNotIn("git apply", page)

    def test_nothing_left_is_named(self) -> None:
        "A patch$ line whose do$ line already writes the whole file has no command, and source_gaps names it for just check."
        facts, _ = self.facts("pyproject.toml", "a" * 40, "")
        found = render.source_gaps(facts)
        self.assertEqual(len(found), 1, found)
        self.assertIn("patch$ pyproject.toml", found[0])
        self.assertEqual(render.source_gaps(self.facts("pyproject.toml", "a" * 40, "@@ -1 +1,2 @@\n a\n+b\n")[0]), [])


SYNC = " && uv sync --locked --all-groups --all-packages"


def take(
    lines: list[int],  # The places of the lines whose files it takes, this one first
    files: list[str],  # The files that it takes
    command: str = "",  # Its command; "" for git restore of the files from cccccccccccc, and uv sync for a uv.lock
    after: bool = False,  # The line runs a program, and the command comes after it
    deletes: tuple[str, ...] = (),  # The files that it deletes
) -> dict:  # A take, as the facts of timewalk 1.4.4 give it
    "Make the take of a do$ line, as timewalk-export --json writes it."
    command = command or "git restore --source cccccccccccc -- " + " ".join(files) + (SYNC if any(f.endswith("uv.lock") for f in files) else "")
    return {"lines": lines, "files": files, "deletes": list(deletes), "command": command, "after": after}


JOINED = {"lines": [], "files": [], "deletes": [], "command": "", "after": False}   # a later line that joins a take


def shows_the_takes(
    test: unittest.TestCase,  # The test, for its asserts
    facts: dict,  # The facts of a tutorial
) -> int:  # How many takes give a command
    """Check that Build it yourself shows exactly the facts' takes: each take's command once, at its line; the line itself
    only when after is true, just before the command; and no line that a take stands for."""
    import follow

    count = 0
    for at, stop in enumerate(facts["stops"], 1):
        commands = [c for block in follow.blocks_of("\n".join(render.stop_page(facts, stop, at, "do", False))) for c in block.commands]
        for change in (stop, *stop["moves"]):
            makes = [p for p in change["parts"] if p["kind"] == "command" and p["makes"]]
            for part in makes:
                found = part["take"]
                if not found:
                    continue
                if found["command"]:
                    count += 1
                    test.assertEqual(commands.count(found["command"]), 1, (found, commands))
                    if found["after"]:
                        test.assertEqual(commands[commands.index(found["command"]) - 1], part["text"], "the line, then the take")
                    for n in found["lines"][1 if found["after"] else 0:]:
                        test.assertNotIn(makes[n]["text"], commands, "a line that the take stands for does not run")
                else:
                    test.assertNotIn(part["text"], commands, "a line that joins a take does not run")
    return count


class Strict(unittest.TestCase):
    "A strict walk: the facts' take of a uv command's line, rendered. timewalk's rule finds the takes; the page shows them."

    def page(
        self,
        found: dict | None,  # The take of the do$ line, from the facts; None: the line runs
        command: str = "uv add --dev ruff",  # The do$ line
        paths: tuple[str, ...] = ("pyproject.toml", "uv.lock"),  # The files that it writes, each by it
        then: bool = False,  # A patch$ line of the first file after it
    ) -> tuple[str, list[str]]:  # Build it yourself's text of the move, and the commands of its blocks
        "Render one move whose do$ line writes the files."
        import follow

        parts = [{"kind": "command", "text": command, "makes": True, "mode": "shared", "track": "", "writes": list(paths), "take": found}]
        parts += [{"kind": "patch", "mode": "shared", "path": paths[0]}] if then else []
        files = [{"path": path, "old_path": None, "status": "modified", "added": 1, "removed": 1, "binary": False,
                  "diff": "@@ -1 +1 @@\n-a\n+b\n", "names": {"added": [], "removed": [], "changed": []}, "by": 0,
                  "patch": "@@ -1 +1 @@\n-a\n+b\n" if then else ""} for path in paths]
        move = {"name": "step-01.1", "number": "1.1", "title": "ruff", "commit": "c" * 40, "parts": parts, "files": files}
        stop = {"name": "step-01", "number": "1", "title": "One", "start": "a" * 40, "commit": "c" * 40, "parts": [], "files": files,
                "moves": [move]}
        facts = {"walk": {"kind": "tutorial", "loose": [], "github": "https://github.com/o/demo"}, "observed": True, "stops": [stop],
                 "history": {}}
        page = "\n".join(render.stop_page(facts, stop, 1, "do", False))
        return page, [c for block in follow.blocks_of(page) for c in block.commands]

    def test_strict_takes_the_files(self) -> None:
        "A take: the page gives its command, git restore of the files and uv sync --locked, and not uv add."
        page, commands = self.page(take([0], ["pyproject.toml", "uv.lock"]))
        self.assertIn("git restore --source cccccccccccc -- pyproject.toml uv.lock" + SYNC, commands)
        self.assertNotIn("uv add --dev ruff", commands)
        self.assertIn("The author ran `uv add --dev ruff` here. It writes `pyproject.toml` and `uv.lock`. On a later day, it can write "
                      "newer versions of packages than the author's, and then git check finds that your files differ. So do not run it.", page)
        self.assertIn("installs exactly the versions that `uv.lock` names:", page)

    def test_no_take_runs_the_command(self) -> None:
        "No take, as in a loose walk, or for a line that is not uv: the page gives the line as it is."
        for line in ("uv add --dev ruff", "sed -i '' s/a/b/ pyproject.toml"):
            page, commands = self.page(None, line)
            self.assertIn(line, commands)
            self.assertNotIn("uv sync --locked", page)
            self.assertNotIn("The author ran", page)

    def test_the_command_of_the_take(self) -> None:
        "The page gives the take's command as the facts have it, an odd path as a literal, with no uv sync without uv.lock."
        command = "git restore --source cccccccccccc -- pyproject.toml .python-version ':(top,literal)src/a[1].py'"
        page, commands = self.page(take([0], ["pyproject.toml", ".python-version", "src/a[1].py"], command), "uv init --lib",
                                   ("pyproject.toml", ".python-version", "src/a[1].py"))
        self.assertIn(command, commands)
        self.assertIn("It takes each file as the author has it from the project:", page)

    def test_patch_after_it(self) -> None:
        "A patch$ line of a file that the student took gives nothing to apply: the file has the change already."
        page, commands = self.page(take([0], ["pyproject.toml", "uv.lock"]), then=True)
        self.assertFalse([c for c in commands if c.startswith("git apply")], commands)
        self.assertIn("nothing to apply", page)
        self.assertIn("and you take it from the project", page)

    def lines(
        self,
        commands: list[tuple[str, list[str], dict | None]],  # Each do$ line, with the files that it writes and its take, in order
        files: dict[str, int],  # Each file of the move, with its by: the last line that writes it
    ) -> tuple[str, list[str], dict]:  # Build it yourself's text of the move, the commands of its blocks, and the facts
        "Render one strict move of several do$ lines."
        import follow

        parts = [{"kind": "command", "text": text, "makes": True, "mode": "shared", "track": "", "writes": writes, "take": found}
                 for text, writes, found in commands]
        found = [{"path": path, "old_path": None, "status": "modified", "added": 1, "removed": 1, "binary": False,
                  "diff": "@@ -1 +1 @@\n-a\n+b\n", "names": {"added": [], "removed": [], "changed": []}, "by": by, "patch": ""}
                 for path, by in files.items()]
        move = {"name": "step-01.1", "number": "1.1", "title": "uv", "commit": "c" * 40, "parts": parts, "files": found}
        stop = {"name": "step-01", "number": "1", "title": "One", "start": "a" * 40, "commit": "c" * 40, "parts": [], "files": found,
                "moves": [move]}
        facts = {"walk": {"kind": "tutorial", "loose": [], "github": "https://github.com/o/demo"}, "observed": True, "stops": [stop],
                 "history": {}}
        page = "\n".join(render.stop_page(facts, stop, 1, "do", False))
        return page, [c for block in follow.blocks_of(page) for c in block.commands], facts

    def test_two_uv_lines(self) -> None:
        "Two uv lines in one take: one command takes their files, and the student runs neither, not even the first."
        both = ["pyproject.toml", "uv.lock"]
        page, commands, facts = self.lines([("uv add six", both, take([0, 1], both)), ("uv add --dev ruff", both, JOINED)],
                                           {"pyproject.toml": 1, "uv.lock": 1})
        self.assertEqual([c for c in commands if c.startswith(("uv", "git restore --source cccccccccccc -- "))],
                         ["git restore --source cccccccccccc -- pyproject.toml uv.lock" + SYNC])
        self.assertIn("The author ran `uv add six`, then `uv add --dev ruff` here. They write", page)
        self.assertEqual(shows_the_takes(self, facts), 1)

    def test_a_joined_line_that_is_not_uv(self) -> None:
        "A sed that joins the take does not run; a line with no take runs."
        page, commands, facts = self.lines([("uv add six", ["pyproject.toml", "uv.lock"], take([0, 1], ["pyproject.toml", "uv.lock"])),
                                            ("sed -i '' s/a/b/ pyproject.toml", ["pyproject.toml"], JOINED),
                                            ("echo x > notes.txt", ["notes.txt"], None)], {"pyproject.toml": 1, "uv.lock": 0, "notes.txt": 2})
        self.assertFalse([c for c in commands if c.startswith(("sed", "uv add"))], commands)
        self.assertIn("echo x > notes.txt", commands)
        self.assertEqual(shows_the_takes(self, facts), 1)

    def test_a_program_runs_and_then_the_take(self) -> None:
        "A take with after: uv run runs a program, so the student runs it, and then the command; a later uv add of its take does not run."
        files = ["data.csv", "pyproject.toml", "uv.lock"]
        page, commands, facts = self.lines([("uv run python make.py", ["data.csv", "uv.lock"], take([0, 1], files, after=True)),
                                            ("uv add ruff", ["pyproject.toml", "uv.lock"], JOINED)], {"data.csv": 0, "pyproject.toml": 1, "uv.lock": 1})
        self.assertEqual(commands, ["uv run python make.py", "git restore --source cccccccccccc -- data.csv pyproject.toml uv.lock" + SYNC, "git check cccccccccccc",
                                    commands[-1]])
        self.assertIn("`uv run python make.py` runs a program, so run it. It also writes `data.csv`, `pyproject.toml` and `uv.lock`.", page)
        self.assertIn("The author then ran `uv add ruff`, which writes the same files, so do not run it. After it, run this command", page)
        self.assertEqual(shows_the_takes(self, facts), 1)

    def test_a_step_of_one_commit(self) -> None:
        "A step with no moves has its own takes in the facts: its page gives the take, and What changed says that the student takes the file."
        import follow

        files = [{"path": path, "old_path": None, "status": "modified", "added": 1, "removed": 1, "binary": False, "diff": "@@ -1 +1 @@\n-a\n+b\n",
                  "names": {"added": [], "removed": [], "changed": []}, "by": 0, "patch": ""} for path in ("pyproject.toml", "uv.lock")]
        parts = [{"kind": "command", "text": "uv add rich", "makes": True, "mode": "shared", "track": "", "writes": ["pyproject.toml", "uv.lock"],
                  "take": take([0], ["pyproject.toml", "uv.lock"])}]
        stop = {"name": "step-02", "number": "2", "title": "Rich", "start": "a" * 40, "commit": "c" * 40, "parts": parts, "files": files, "moves": []}
        facts = {"walk": {"kind": "tutorial", "loose": [], "github": "https://github.com/o/demo"}, "observed": True,
                 "stops": [{**stop, "name": "step-01", "start": None, "parts": [], "commit": "a" * 40}, stop], "history": {}}
        page = "\n".join(render.stop_page(facts, stop, 2, "do", False))
        commands = [c for block in follow.blocks_of(page) for c in block.commands]
        self.assertIn("git restore --source cccccccccccc -- pyproject.toml uv.lock" + SYNC, commands)
        self.assertNotIn("uv add rich", commands)
        self.assertIn("It comes from `uv add rich`, and you take it from the project.", page)
        self.assertEqual(shows_the_takes(self, {**facts, "stops": [stop]}), 1)

    def test_old_facts_stop(self) -> None:
        "Facts of a timewalk before 1.4.4 stop the render with a message to update timewalk: an older layout, or a do$ line with no take."
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "facts.json"
            part = {"kind": "command", "text": "uv add x", "makes": True, "mode": "shared", "track": "", "writes": None}
            facts = {"format": 4, "timewalk": "1.4.3", "walk": {"kind": "tutorial"}, "stops": [{"parts": [], "moves": [{"parts": [part]}]}]}
            for layout, made in ((3, part), (4, part), (4, {**part, "take": take([0], ["uv.lock"]) | {"after": None}} )):
                made_facts = {**facts, "format": layout, "stops": [{"parts": [], "moves": [{"parts": [made]}]}]}
                if layout == 4 and "take" in made:
                    del made["take"]["after"]
                path.write_text(json.dumps(made_facts))
                with self.assertRaises(SystemExit) as stopped:
                    render.load(path)
                self.assertIn("update timewalk to 1.4.4 or later", str(stopped.exception))
            path.write_text(json.dumps({**facts, "stops": [{"parts": [], "moves": [{"parts": [{**part, "take": None}]}]}]}))
            self.assertEqual(render.load(path)["format"], 4)

    def test_the_title_of_toc(self) -> None:
        "timewalk-export gets the title that toc.toml gives the walk, so a strict walk on the tutorial's notes has a name of its own."
        with tempfile.TemporaryDirectory() as folder:
            toc = Path(folder) / "toc.toml"
            toc.write_text('[[walk]]\nid = "a"\nkind = "tutorial"\nfolder = "w"\ntitle = "Exact"\n\n[[walk]]\nid = "b"\nkind = "tutorial"\nfolder = "w"\n')
            for ident, wanted in (("a", ["--title", "Exact"]), ("b", [])):
                with mock.patch.object(render.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "no")) as run:
                    with self.assertRaises(render.PagesError):
                        render.export(Path(folder), toc, ident, "https://github.com/o/demo", Path(folder))
                args = run.call_args.args[0]
                self.assertEqual(args[args.index("--github") + 2:], wanted)

    def test_a_strict_walk_gets_pages(self) -> None:
        "A walk that differs from another only by loose gets pages of its own."
        with tempfile.TemporaryDirectory() as folder:
            toc = Path(folder) / "toc.toml"
            toc.write_text('[[walk]]\nid = "a"\nkind = "tutorial"\nfolder = "w"\nloose = ["uv.lock"]\n\n'
                           '[[walk]]\nid = "b"\nkind = "tutorial"\nfolder = "w"\n')
            self.assertEqual([entry["id"] for entry in render.page_walks(toc)], ["a", "b"])


TALLY = Path(os.environ.get("TIMEWALK_TEST", Path.home() / "Projects" / "timewalk-test"))


@unittest.skipUnless((TALLY / "history" / "build.py").is_file() and shutil.which("uvx"), "timewalk-test or uv is not here")
class FactsTakes(unittest.TestCase):
    "The pages of timewalk-test's strict walks, from timewalk's own facts: Build it yourself shows exactly each take of the facts."

    def test_the_page_shows_exactly_the_facts_take(self) -> None:
        "Every take of the walks strict and strict-extra: its command once, at its line, and no line that it stands for."
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder) / "repo"
            subprocess.run([sys.executable, str(TALLY / "history" / "build.py"), str(repo)], check=True, capture_output=True)
            count = 0
            for ident in ("strict", "strict-extra"):
                facts = render.export(repo, TALLY / "toc.toml", ident, "https://github.com/rahuldave/tally", Path(folder))
                self.assertTrue(facts["observed"])
                count += shows_the_takes(self, facts)
            self.assertGreaterEqual(count, 5, "ruff in strict; tabulate, mdformat, the library, talib and the remove in strict-extra")


class StrictUv(Case):
    "A student follows a strict move with real uv: the page's command takes the files, installs them, and git check passes."

    def follow(
        self,
        made: list[str],  # The author's commands of the move, run in the project
        then: str,  # What the student runs after the move, which must work
        setup: str = "true",  # A command for the project before the move, at its start
    ) -> None:
        "Make the move with uv, render its page, run its commands in a learner's clone as follow.py does, then run then."
        if not shutil.which("uv"):
            self.skipTest("uv is not installed")
        import follow

        sh(self.repo, f"uv init -q --name demo --author-from none . && uv lock -q && {setup}")
        start = commit(self.repo, {}, "start")
        before = set(sh(self.repo, "git ls-files").stdout.split())
        for command in made:
            sh(self.repo, command)
        sha = commit(self.repo, {}, "move")
        paths = sh(self.repo, f"git diff --name-only {start} {sha}").stdout.split()
        kept = sorted(path for path in paths if (self.repo / path).exists())
        command = (f"git restore --source {sha[:12]} -- " + " ".join(kept)
                   + "".join(f" && uv sync{' --directory ' + p.rsplit('/', 1)[0] if '/' in p else ''} --locked --all-groups --all-packages"
                             for p in kept if p.endswith("uv.lock")))
        found_take = {"lines": [0], "files": kept, "deletes": [], "command": command, "after": False}   # as timewalk's facts give it
        parts = [{"kind": "command", "text": "; ".join(made), "makes": True, "mode": "shared", "track": "", "writes": paths, "take": found_take}]
        found = [{"path": path, "old_path": None, "status": "modified" if path in before else "added", "added": 1, "removed": 0,
                  "binary": False, "diff": "", "names": {"added": [], "removed": [], "changed": []}, "by": 0, "patch": ""} for path in paths]
        move = {"name": "step-01.1", "number": "1.1", "title": "uv", "commit": sha, "parts": parts, "files": found}
        stop = {"name": "step-01", "number": "1", "title": "One", "start": start, "commit": sha, "parts": [], "files": found, "moves": [move]}
        facts = facts_of([], [sha]) | {"observed": True, "stops": [stop], "history": {}}
        page = "\n".join(render.stop_page(facts, stop, 1, "do", False))
        work = self.learner(facts, start)
        sh(work, "uv sync -q")
        for block in follow.blocks_of(page):
            for command in block.commands:
                self.assertFalse(command.startswith("uv add"), command)
                sh(work, command)
        self.assertEqual(sh(work, f"git check {sha}").stdout, "")
        sh(work, then)

    def test_a_group_then_its_tool(self) -> None:
        "uv add --group docs mdformat, then uv run mdformat: uv sync --locked alone installs only the default groups, and mdformat is missing."
        self.follow(["uv add -q --group docs mdformat"], "uv run mdformat --version")

    def test_a_package_of_a_workspace(self) -> None:
        "uv add --package to a member that the project does not depend on: uv sync --locked alone leaves the member out."
        self.follow(["uv init -q --lib --author-from none packages/m", "uv add -q --package m six"], "uv run python -c 'import m, six'")

    def test_remove(self) -> None:
        "uv remove: the student's uv.lock and environment lose the package, as the author's do."
        self.follow(["uv remove -q six"], "! uv run python -c 'import six'", "uv add -q six")

    def test_version(self) -> None:
        "uv version --bump writes the version into pyproject.toml and uv.lock."
        self.follow(["uv version -q --bump minor"], "grep -q 'version = \"0.2.0\"' pyproject.toml")

    def test_a_member(self) -> None:
        "uv init of a member writes its files and the workspace's list in the top pyproject.toml, and the member's own pyproject.toml is exact."
        self.follow(["uv init -q --lib --author-from none packages/m", "uv add -q ./packages/m"], "uv run python -c 'import m'")


class WalkSites(unittest.TestCase):
    "One website in site/: the first walk's pages at the top, each other walk's in site/ID/, and one _smalldocs.yml."

    @staticmethod
    def facts(ident: str, title: str, description: str) -> dict:
        "The facts of a narrative with no stops."
        walk = {"id": ident, "title": title, "description": description, "kind": "narrative", "mode": "watch", "github": "https://github.com/o/demo"}
        return {"walk": walk, "intro": [], "stops": [], "history": {}, "errors": [], "observed": True}

    def pages(self, walks: dict) -> dict[str, str]:
        "Render the pages of these walks, in order."
        with mock.patch.object(render, "export", lambda repo, toc, ident, *args: walks[ident]), \
                mock.patch.object(render, "toml_edits", lambda *args: {}), \
                mock.patch.object(render, "page_walks", lambda toc: [{"id": ident} for ident in walks]):
            pages, _, _ = render.class_pages(Path("toc.toml"), Path("."), "https://github.com/o/demo")
        return pages

    def test_one_project(self) -> None:
        "One _smalldocs.yml renders every walk's pages, with a sidebar of its own for each walk, whose links are from site/."
        walks = {"first": self.facts("first", "The first", "One."), "second": self.facts("second", "Second", "Two.")}
        walks["second"]["stops"] = [{"name": "step-01", "number": "1", "title": "One", "moves": [], "parts": [], "commit": "0" * 40}]
        with mock.patch.object(render, "stop_page", lambda *args: ["Text."]):
            pages = self.pages(walks)
        self.assertEqual([name for name in pages if name.endswith(".yml")], ["site/_smalldocs.yml"])
        self.assertEqual([name for name in pages if name.endswith(".css")], ["site/styles.css"])
        self.assertFalse(any(name.startswith("sites/") for name in pages))
        self.assertIn("site/second/read/step-01.qmd", pages)
        config = pages["site/_smalldocs.yml"]
        self.assertIn('  render: ["index.qmd", "read/*.qmd", "second/index.qmd", "second/read/*.qmd"]', config)
        self.assertIn('website:\n  title: "The first"\n', config)
        self.assertIn('  sidebar:\n    - title: "The first"\n      style: docked\n      contents:\n        - index.qmd\n', config)
        self.assertIn('    - title: "Second"\n      style: docked\n      contents:\n        - second/index.qmd\n', config)
        self.assertIn('            - text: "1 One"\n              href: second/read/step-01.qmd\n', config)

    def test_an_id_that_clashes(self) -> None:
        "A walk after the first may not have an id that the first walk uses at the top of site/, in any case."
        for ident in ("read", "build", "index", "site_libs", "search.json", "Read"):
            walks = {"first": self.facts("first", "The first", ""), ident: self.facts(ident, "Other", "")}
            with self.assertRaisesRegex(render.PagesError, f"walk {re.escape(ident)}: the website has"):
                self.pages(walks)
        for ident in ("_x", "env", "Venv", "node_modules"):   # folders that smalldocs leaves out
            walks = {"first": self.facts("first", "The first", ""), ident: self.facts(ident, "Other", "")}
            with self.assertRaisesRegex(render.PagesError, f"walk {re.escape(ident)}: smalldocs leaves out"):
                self.pages(walks)
        self.assertIn("site/tests/index.qmd", self.pages({"first": self.facts("first", "The first", ""), "tests": self.facts("tests", "T", "")}))

    def test_links(self) -> None:
        "class_pages links the first walk's front page to each other walk at ID/, and each other walk's back to ../."
        facts = self.facts
        walks = {"first": facts("first", "The first", "One."), "second": facts("second", "The [second]", "Two"), "third": facts("third", "Third", "")}
        pages = self.pages(walks)
        front = pages["site/index.qmd"]
        self.assertIn("- [The \\[second\\]](second/index.html). Two.", front)
        self.assertIn("- [Third](third/index.html).", front)
        self.assertNotIn("](first/", front)
        for ident in ("second", "third"):
            self.assertIn("[The first](../)", pages[f"site/{ident}/index.qmd"])
            self.assertNotIn("The other walks", pages[f"site/{ident}/index.qmd"])


class OurWords(unittest.TestCase):
    "timewalk's words in the prose that a reader reads."

    def test_hyphenated(self) -> None:
        "A word such as pre-commit is not commit, but a name such as step-02 is still step."
        self.assertEqual(render.OUR_WORDS.findall("run pre-commit, then the commit-msg hook, step-by-step"), [])
        self.assertEqual(render.OUR_WORDS.findall("see step-02, and the commit."), ["step", "commit"])

    def test_description(self) -> None:
        "The walk's description, which the first walk's website lists, is checked too."
        facts = {"walk": {"title": "Only the tests", "description": "Three commits of tally"}, "intro": [], "stops": []}
        found = render.our_words(facts)
        self.assertEqual(len(found), 1, found)
        self.assertIn("the walk's description", found[0])



if __name__ == "__main__":
    unittest.main()
