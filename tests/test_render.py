"""Tests of render.py's commands for Build it yourself: git check, the lock of a move, and the patch of a renamed file.

    python3 -m unittest discover -s tests

Each test makes a small git repository in a temporary folder. The lock tests need uv, and run offline.
"""

import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
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
    "A temporary folder, and a cache of the lock checks of its own."

    def setUp(self) -> None:
        "Make the folder, and send the cache of the lock checks there."
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.cache = os.environ.get("XDG_CACHE_HOME")
        os.environ["XDG_CACHE_HOME"] = str(self.folder / "cache")
        self.addCleanup(lambda: os.environ.pop("XDG_CACHE_HOME") if self.cache is None else os.environ.update(XDG_CACHE_HOME=self.cache))
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
        self.assertIn("D\tuv.lock", found.stdout)
        self.assertNotIn("six", found.stdout)
        self.assertEqual(sh(work, "git diff --cached --name-only").stdout, "")


class StaleLock(Case):
    "A move whose own uv.lock is out of date gets git check --stale-lock, and a learner with its files passes."

    def setUp(self) -> None:
        "A project whose second commit changes pyproject.toml and not uv.lock, and whose third runs uv lock."
        super().setUp()
        if not shutil.which("uv"):
            self.skipTest("uv is not installed")
        (self.repo / "pyproject.toml").write_text(PYPROJECT)
        sh(self.repo, "uv lock -q --offline")
        self.start = commit(self.repo, {}, "start")
        self.stale = commit(self.repo, {"pyproject.toml": PYPROJECT.replace("0.1.0", "0.2.0")}, "a new version")
        sh(self.repo, "uv lock -q --offline")
        self.locked = commit(self.repo, {}, "uv lock")
        self.facts = facts_of(["pyproject.toml", "uv.lock"], [self.stale, self.locked])

    def test_found(self) -> None:
        "The second commit alone is stale, and the result is kept in the cache."
        self.assertEqual(render.stale_locks(self.repo, self.facts), [self.stale])
        version = subprocess.run(["uv", "--version"], capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual((render.lock_cache() / render.lock_key(self.repo, self.stale, version)).read_text(), "stale\n")
        self.assertEqual((render.lock_cache() / render.lock_key(self.repo, self.locked, version)).read_text(), "current\n")
        self.assertEqual(sh(self.repo, "git status --porcelain").stdout, "")

    def test_without_loose(self) -> None:
        "A walk whose loose does not name uv.lock compares uv.lock line by line, and runs no uv lock --check."
        self.assertEqual(render.stale_locks(self.repo, facts_of([], [self.stale, self.locked])), [])

    def test_learner_passes(self) -> None:
        "The page gives --stale-lock at the stale move, and a learner whose files are the commit's passes there."
        self.facts["stale_locks"] = render.stale_locks(self.repo, self.facts)
        page = render.Page(self.facts, "do", False)
        page.check(self.stale, self.start, "move")
        page.check(self.locked, self.stale, "move")
        lines = [line for line in page.lines if line.startswith("git check")]
        self.assertEqual(lines, [f"git check {self.stale[:12]} {render.STALE_LOCK}", f"git check {self.locked[:12]}"])
        work = self.learner(self.facts, self.start)
        sh(work, f"git restore --source {self.stale} --worktree -- :/")
        self.assertNotEqual(sh(work, f"git check {self.stale}", check=False).returncode, 0)
        done = sh(work, lines[0], check=False)
        self.assertEqual((done.returncode, done.stdout + done.stderr), (0, ""))
        sh(work, f"git restore --source {self.locked} --worktree -- :/")
        done = sh(work, lines[1], check=False)
        self.assertEqual((done.returncode, done.stdout + done.stderr), (0, ""))


class LockCheck(Case):
    "uv lock --check sees only the project's own files and settings, keeps its answer by those files, and says when it cannot tell."

    def setUp(self) -> None:
        "A project with a current uv.lock at its one commit."
        super().setUp()
        if not shutil.which("uv"):
            self.skipTest("uv is not installed")
        (self.repo / "pyproject.toml").write_text(PYPROJECT)
        sh(self.repo, "uv lock -q --offline")
        self.sha = commit(self.repo, {}, "start")

    def stale(
        self,
        sha: str = "",  # The commit (default: the one commit)
    ) -> list[str]:  # What stale_locks finds
        "Find the stale commits of a walk with the one move."
        return render.stale_locks(self.repo, facts_of(["pyproject.toml", "uv.lock"], [sha or self.sha]))

    def uv_runs(self) -> list[list[str]]:  # Each uv lock command that render runs from now on
        "Count the runs of uv lock, and still run them."
        runs, real = [], subprocess.run

        def run(args, *rest, **options):
            if args[:2] == ["uv", "lock"]:
                runs.append(args)
            return real(args, *rest, **options)
        patcher = mock.patch.object(render.subprocess, "run", run)
        patcher.start()
        self.addCleanup(patcher.stop)
        return runs

    def test_author_settings_ignored(self) -> None:
        "A UV_ variable and a uv.toml of the author's own, which would make uv lock --check fail, do not make the lock stale."
        config = self.folder / "config" / "uv"
        config.mkdir(parents=True)
        (config / "uv.toml").write_text('resolution = "lowest-direct"\n')
        environ = {"UV_EXCLUDE_NEWER": "2020-01-01T00:00:00Z", "UV_DEFAULT_INDEX": "https://mirrors.example.invalid/simple/",
                   "XDG_CONFIG_HOME": str(self.folder / "config")}
        self.assertNotEqual(sh(self.repo, "UV_EXCLUDE_NEWER=2020-01-01T00:00:00Z uv lock --check -q --offline", check=False).returncode, 0)
        with mock.patch.dict(os.environ, environ):
            self.assertEqual(self.stale(), [])

    def test_project_settings_kept(self) -> None:
        "The project's own [tool.uv], an index of its own and exclude-newer, still decides: such a lock is current."
        wheels = self.folder / "wheels"
        wheels.mkdir()
        with zipfile.ZipFile(wheels / "tiny-1.0-py3-none-any.whl", "w") as wheel:
            wheel.writestr("tiny/__init__.py", "")
            wheel.writestr("tiny-1.0.dist-info/METADATA", "Metadata-Version: 2.1\nName: tiny\nVersion: 1.0\n")
            wheel.writestr("tiny-1.0.dist-info/WHEEL", "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
            wheel.writestr("tiny-1.0.dist-info/RECORD", "")
        own = (PYPROJECT.replace("[]", '["tiny"]') + '\n[tool.uv]\nexclude-newer = "2024-01-01T00:00:00Z"\n\n'
               f'[[tool.uv.index]]\nname = "local"\nurl = "{wheels}"\nformat = "flat"\n')
        (self.repo / "pyproject.toml").write_text(own)
        sh(self.repo, "uv lock -q --offline")
        sha = commit(self.repo, {}, "own settings")
        self.assertEqual(sh(self.repo, "uv lock --check -q --offline --no-config", check=False).returncode != 0, True,
                         "--no-config would leave out the project's own exclude-newer")
        self.assertEqual(self.stale(sha), [])

    def test_cache_by_files(self) -> None:
        "A retag, with new commits but the same pyproject.toml and uv.lock, runs no uv lock again; another uv version is another key."
        self.assertEqual(self.stale(), [])
        runs = self.uv_runs()
        sh(self.repo, "git commit -q --amend -m 'start, again'")
        again = commit(self.repo, {"README.md": "new\n"}, "a fix to an earlier step")
        self.assertEqual(self.stale(again), [])
        self.assertEqual(runs, [])
        self.assertNotEqual(render.lock_key(self.repo, again, "uv 1.0"), render.lock_key(self.repo, again, "uv 2.0"))
        member = commit(self.repo, {"member/pyproject.toml": PYPROJECT.replace("demo", "member")}, "a member")
        self.assertNotEqual(render.lock_key(self.repo, again, "uv 1.0"), render.lock_key(self.repo, member, "uv 1.0"))

    def test_undecided_is_an_error(self) -> None:
        "A commit that uv cannot decide is an error that names the commit, and nothing is kept in the cache."
        bad = commit(self.repo, {"pyproject.toml": "[project\n"}, "broken")
        with self.assertRaises(render.PagesError) as caught:
            self.stale(bad)
        self.assertIn(bad[:12], str(caught.exception))
        self.assertIn("install uv", str(caught.exception))
        self.assertFalse(any(render.lock_cache().glob("*")) if render.lock_cache().is_dir() else False)

    def test_no_uv_is_an_error(self) -> None:
        "Without uv, a walk whose loose names uv.lock cannot be rendered with --repo."
        with mock.patch.object(render.shutil, "which", return_value=None), self.assertRaises(render.PagesError):
            self.stale()

    def test_links(self) -> None:
        "A project with an absolute symlink and one that leaves the project is checked, and no link is followed."
        sh(self.repo, "ln -s /etc/hosts hosts-link && ln -s ../../x esc")
        sha = commit(self.repo, {}, "links")
        self.assertEqual(self.stale(sha), [])

    def test_workspace(self) -> None:
        "A workspace with a member, whose README the build backend names, is checked with every file it needs."
        root = PYPROJECT.replace("[]", '["member"]') + '\n[tool.uv.sources]\nmember = { workspace = true }\n\n[tool.uv.workspace]\nmembers = ["packages/*"]\n'
        member = (PYPROJECT.replace("demo", "member") + 'readme = "README.md"\n\n[build-system]\nrequires = ["uv_build"]\n'
                  'build-backend = "uv_build"\n')
        commit(self.repo, {"pyproject.toml": root, "packages/member/pyproject.toml": member, "packages/member/README.md": "hi\n",
                           "packages/member/src/member/__init__.py": ""}, "workspace")
        sh(self.repo, "uv lock -q --offline")
        sha = commit(self.repo, {}, "lock")
        self.assertEqual(self.stale(sha), [])

    def test_check_class_error(self) -> None:
        "check_class reports a commit that the project lacks as a problem of the walk, not a traceback."
        facts = facts_of(["pyproject.toml", "uv.lock"], ["0" * 40])
        facts["errors"] = []
        out = io.StringIO()
        with mock.patch.object(render, "page_walks", return_value=[{"id": "w"}]), mock.patch.object(render, "export", return_value=facts), \
                contextlib.redirect_stdout(out):
            self.assertEqual(render.check_class(self.folder, self.repo, "https://github.com/o/demo"), 1)
        self.assertIn("walk w: ", out.getvalue())
        self.assertIn("does not have commit", out.getvalue())


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



class IndexCommands(unittest.TestCase):
    "A git rm or git mv on a page fails for a student who never commits, so the check of a class names it."

    def facts(self, *texts: str) -> dict:
        "Facts of one move with these commands."
        parts = [{"kind": "command", "text": text, "makes": True, "mode": "shared"} for text in texts]
        return {"stops": [{"moves": [{"name": "step-01.1", "parts": parts}]}]}

    def test_found(self) -> None:
        "git rm, git mv, and either after && are named."
        found = render.index_commands(self.facts("git rm old.py", "git mv a.py b.py", "uv lock && git rm -r build"))
        self.assertEqual(len(found), 3, found)
        self.assertIn("Write `mv`", found[1])

    def test_others_pass(self) -> None:
        "rm, mv, git restore and a word that only starts like it are not named."
        self.assertEqual(render.index_commands(self.facts("rm old.py", "mv a.py b.py", "git restore x", "git rmdir", "echo git-rm")), [])

    def test_check_class_counts_it(self) -> None:
        "just check, through check_class, counts a git mv on a page of a tutorial as a problem."
        facts = self.facts("git mv a.py b.py")
        facts["walk"] = {"kind": "tutorial", "loose": []}
        saved = render.export, render.stale_locks, render.page_walks, render.source_gaps, render.markdown_files, render.our_words
        self.addCleanup(lambda: setattr(render, "export", saved[0]) or setattr(render, "stale_locks", saved[1])
                        or setattr(render, "page_walks", saved[2]) or setattr(render, "source_gaps", saved[3])
                        or setattr(render, "markdown_files", saved[4]) or setattr(render, "our_words", saved[5]))
        render.export = lambda *args: facts
        render.stale_locks = lambda *args: []
        render.page_walks = lambda toc: [{"id": "w"}]
        render.source_gaps = render.our_words = lambda facts: []
        render.markdown_files = lambda facts: {}
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(render.check_class(Path(folder), Path(folder), "https://github.com/o/demo"), 1)

    def test_a_git_mv_fails_for_the_student(self) -> None:
        "The reason: after git check, git mv of a file that the student made is refused."
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            sh(work, "git init -q -b main && echo a > f && git add f && git commit -qm a")
            for line in render.check_lines({"walk": {"loose": []}}):
                sh(work, line)
            sh(work, "echo n > new.py && git check HEAD > /dev/null")
            self.assertNotEqual(sh(work, "git mv new.py other.py", check=False).returncode, 0)
            self.assertEqual(sh(work, "mv new.py other.py").returncode, 0)


if __name__ == "__main__":
    unittest.main()
