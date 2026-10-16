"""Tests of a class from start to end, on timewalk-test's tally, and of private.py, pdf_check.py and style_sync.py.

    python3 -m unittest discover -s tests

`Class` copies timewalk-test (TIMEWALK_TEST, default ~/Projects/timewalk-test) into a temporary folder: a clone of its
repo/, and its toc.toml, notes and slides. It runs class_init, walk_init and walk_update there, and the walk repository's
justfile as a student runs it, with git kept off the network. It never writes into timewalk-test. walk_update gets
timewalk from TIMEWALK, as the scripts do. The tests need git, just and uv, and actionlint through uvx.
"""

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

KIT = Path(__file__).resolve().parent.parent
SCRIPTS = KIT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import class_init
import render
import pdf_check
import walk_init
from common import GITHUB, fill
from private import PRIVATE, MixedCue, fenced, in_code, private_lines, public, toml_cues

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_review import copy_of_timewalk_test

TIMEWALK_TEST = Path(os.environ.get("TIMEWALK_TEST", Path.home() / "Projects" / "timewalk-test")).expanduser()
ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
       "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "GIT_TERMINAL_PROMPT": "0"}
KEY = re.compile(r"@[A-Za-z_]+@")  # a @key@ of a template that was not filled
VALUES = {"project": "tally", "upstream": "o", "timewalk": GITHUB}  # what walk_init gives the walk templates


def git(
    cwd: Path,  # The repository
    *args: str,  # Arguments to git
) -> str:  # What git printed, without the trailing newline
    "Run git, and fail the test if it fails."
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, env=ENV, check=False)
    if done.returncode:
        raise AssertionError(f"git {' '.join(args)} failed in {cwd}: {done.stderr}")
    return done.stdout.rstrip("\n")


def script(
    name: str,  # A script of walk-kit, such as "walk_init.py"
    *args: str,  # Its arguments
    cwd: Path,  # Where to run it
    env: dict | None = None,  # The environment (default: ENV)
) -> subprocess.CompletedProcess:  # What it printed, and its exit code
    "Run a script of walk-kit as the class justfile does, with no terminal to answer its questions."
    return subprocess.run([sys.executable, str(SCRIPTS / name), *args], cwd=cwd, capture_output=True, text=True, env=env or ENV,
                          stdin=subprocess.DEVNULL, check=False)


def files_of(
    folder: Path,  # A repository or a folder
) -> dict[str, str]:  # Each file by its path from the folder, outside .git, with its text
    "Read every file of a folder."
    return {path.relative_to(folder).as_posix(): path.read_bytes().decode("utf-8", errors="replace")
            for path in sorted(folder.rglob("*")) if path.is_file() and ".git" not in path.relative_to(folder).parts}


def just(
    cwd: Path,  # The folder of the justfile
    *args: str,  # The recipe and its arguments
    env: dict,  # The environment
) -> subprocess.CompletedProcess:  # What it printed, and its exit code
    "Run a recipe as a student types it."
    return subprocess.run(["just", *args], cwd=cwd, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, check=False)


def tools() -> str | None:  # What is missing for the end-to-end tests, or None
    "Say what the end-to-end tests lack on this machine."
    if not (TIMEWALK_TEST / "history" / "build.py").exists():
        return f"{TIMEWALK_TEST} is not timewalk-test; set TIMEWALK_TEST"
    missing = [tool for tool in ("git", "just", "uv", "uvx") if not shutil.which(tool)]
    return f"{', '.join(missing)} not on this machine" if missing else None


@unittest.skipIf(tools(), tools())
class Class(unittest.TestCase):
    "A class for tally from class_init, its walk repository from walk_init, and walk_update with timewalk-test's 9 walks."

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp())
        cls.repo, cls.folder, cls.walk = cls.tmp / "tally", cls.tmp / "tally-class", cls.tmp / "tally-walk"
        (cls.tmp / "source").mkdir()
        source = copy_of_timewalk_test(TIMEWALK_TEST, cls.tmp / "source")   # as last committed: no edit in progress reaches the test
        git(cls.tmp, "clone", "--quiet", str(source / "repo"), str(cls.repo))
        # A gh that notes each call: the scripts must not run gh without a typed yes
        fake = cls.tmp / "bin"
        fake.mkdir()
        (fake / "gh").write_text(f"#!/bin/sh\necho \"$@\" >> {cls.tmp / 'gh-calls'}\n")
        (fake / "gh").chmod(0o755)
        cls.env = {**ENV, "PATH": f"{fake}{os.pathsep}{ENV['PATH']}"}
        cls.class_run = script("class_init.py", "--project", "tally", "--upstream", "o", "--repo", str(cls.repo), "--dir", str(cls.folder),
                               "--toc", cwd=cls.tmp, env=cls.env)
        cls.class_files = files_of(cls.folder) if cls.folder.is_dir() else {}
        cls.walk_run = script("walk_init.py", "--project", "tally", "--upstream", "o", "--walk", str(cls.walk), "--no-github",
                              cwd=cls.tmp, env=cls.env)
        cls.walk_files = files_of(cls.walk) if cls.walk.is_dir() else {}
        cls.walk_commits = git(cls.walk, "log", "--format=%H").split() if (cls.walk / ".git").is_dir() else []
        # The material of timewalk-test's 9 walks, in place of what class_init wrote
        for name in ("toc.toml", "notes.md"):
            shutil.copy(source / name, cls.folder / name)
        for name in ("slides", "walks"):
            shutil.copytree(source / name, cls.folder / name, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
        cls.update = cls.walk_update("--repo", str(cls.repo))
        git(cls.walk, "add", "-A")
        git(cls.walk, "commit", "--quiet", "-m", "The walk, from the class notes")

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @classmethod
    def walk_update(
        cls,
        *args: str,  # More arguments
        walk: Path | None = None,  # The walk repository (default: the class's)
    ) -> subprocess.CompletedProcess:  # What it printed, and its exit code
        "Run walk_update on every walk of toc.toml, as just walk-update does, with no terminal to say yes."
        return script("walk_update.py", "--project", "tally", "--upstream", "o", "--toc", str(cls.folder / "toc.toml"),
                      "--walk", str(walk or cls.walk), *args, cwd=cls.folder, env=cls.env)

    def walk_clone(
        self,
        name: str,  # The folder of the clone, in the temporary folder
        at: str = "HEAD",  # The commit to put it at
    ) -> Path:  # A clone of the walk repository, at that commit
        "Clone the walk repository, so that a test changes a copy of its own."
        clone = self.tmp / name
        git(self.tmp, "clone", "--quiet", str(self.walk), str(clone))
        git(clone, "reset", "--quiet", "--hard", at)
        return clone

    def test_class_init_writes_the_class(self) -> None:
        self.assertEqual(self.class_run.returncode, 0, self.class_run.stderr)
        self.assertEqual(set(self.class_files), {".gitignore", "AGENTS.md", "CLAUDE.md", "README.md", "justfile", "notes.md", "toc.toml",
                                                 "slides/slides.example.toml"})
        for name, text in self.class_files.items():
            self.assertIsNone(KEY.search(text), f"{name} keeps a @key@")
        self.assertEqual(self.class_files["CLAUDE.md"], "@AGENTS.md\n")
        # The project and the walk repository sit beside the class folder, so a clone on another machine finds them there
        justfile = self.class_files["justfile"]
        self.assertIn('repo := env("PROJECT_DIR", parent_directory(justfile_directory()) / "tally")', justfile)
        self.assertIn('walk := env("WALK_DIR", parent_directory(justfile_directory()) / "tally-walk")', justfile)
        self.assertIn(f'timewalk := env("TIMEWALK", "{GITHUB}")', justfile)
        # notes.md: one section for each step tag, in order, with the first line of its note as the title
        tags = git(self.repo, "tag", "-l", "step-*", "--sort=version:refname").split()
        titles = [git(self.repo, "tag", "-l", "--format=%(contents:subject)", tag) for tag in tags]
        self.assertEqual(re.findall(r"^## (\S+) (.*)$", self.class_files["notes.md"], re.MULTILINE), list(zip(tags, titles, strict=True)))
        self.assertEqual(len(tags), 7)
        self.assertEqual(tomllib.loads(self.class_files["toc.toml"])["walk"][0]["notes"], "notes.md")
        # One commit, with every file, and nothing on GitHub without a typed yes
        self.assertEqual(git(self.folder, "rev-list", "--count", "HEAD"), "1")
        self.assertEqual(set(git(self.folder, "ls-tree", "-r", "--name-only", "HEAD^{commit}").split("\n")), set(self.class_files))
        self.assertIn("nothing on GitHub", self.class_run.stdout)
        self.assertFalse((self.tmp / "gh-calls").exists(), "class_init ran gh without a yes")

    def test_class_justfile_parses(self) -> None:
        done = subprocess.run(["just", "--justfile", str(self.folder / "justfile"), "--summary"], capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        for recipe in ("setup", "present", "check", "style", "draft", "pdf", "check-pdf", "walk-init", "walk-update"):
            self.assertIn(recipe, done.stdout.split())

    def test_class_init_refuses(self) -> None:
        taken = script("class_init.py", "--project", "tally", "--upstream", "o", "--repo", str(self.repo), "--dir", str(self.folder),
                       "--no-github", cwd=self.tmp)
        self.assertEqual(taken.returncode, 2)
        self.assertIn("is not empty", taken.stderr)
        no_git = script("class_init.py", "--project", "tally", "--upstream", "o", "--repo", str(self.tmp / "bin"), "--dir",
                        str(self.tmp / "other-class"), "--no-github", cwd=self.tmp)
        self.assertEqual(no_git.returncode, 2)
        self.assertFalse((self.tmp / "other-class").exists())

    def test_walk_init_makes_one_commit(self) -> None:
        self.assertEqual(self.walk_run.returncode, 0, self.walk_run.stderr)
        self.assertEqual(set(self.walk_files), {"justfile", ".gitignore", "README.md", "AGENTS.md", "CLAUDE.md", "walk.md",
                                                ".github/workflows/pages.yml"})
        self.assertEqual(len(self.walk_commits), 1)
        self.assertEqual(set(git(self.walk, "ls-tree", "-r", "--name-only", self.walk_commits[-1]).split("\n")), set(walk_init.FILES))
        for name, text in self.walk_files.items():
            self.assertIsNone(KEY.search(text), f"{name} keeps a @key@")
            self.assertEqual(text, fill(walk_init.FILES[name], VALUES), name)
        self.assertIn("--replay worktree", self.walk_files["justfile"])
        self.assertFalse((self.tmp / "gh-calls").exists(), "walk_init ran gh with --no-github")
        again = script("walk_init.py", "--project", "tally", "--upstream", "o", "--walk", str(self.walk), "--no-github", cwd=self.tmp)
        self.assertEqual(again.returncode, 2)

    def test_walk_update_writes_every_walk(self) -> None:
        self.assertEqual(self.update.returncode, 0, self.update.stderr)
        files = files_of(self.walk)
        ids = [walk["id"] for walk in tomllib.loads((self.folder / "toc.toml").read_text())["walk"]]
        self.assertGreaterEqual(len(ids), 9)
        for number, ident in enumerate(ids):
            self.assertIn(f"walks/{ident}/read.md", files)
            self.assertIn(f"({ident}/read.md)", files["walks/README.md"])
            self.assertTrue(any(name.startswith("site/" if not number else f"site/{ident}/") for name in files), ident)
        self.assertNotIn("walk.md", files)
        self.assertEqual(files["toc.toml"], (self.folder / "toc.toml").read_text())
        for name, text in files.items():
            self.assertIsNone(KEY.search(text), f"{name} keeps a @key@")

    def test_no_private_line_reaches_the_walk(self) -> None:
        # What private.py drops from each file of the class: the cue lines themselves, and planned times
        cues = set()
        for path in sorted(self.folder.rglob("*")):
            if path.suffix in (".md", ".toml") and ".git" not in path.parts:
                text = path.read_text(encoding="utf-8")
                lines = text.split("\n")
                cues |= {lines[at].strip() for at in private_lines(text) if any(rule.match(lines[at]) for rule in PRIVATE)}
        self.assertGreater(len([cue for cue in cues if cue.startswith("> Say:")]), 3, "the class has no cues to leave out")
        self.assertIn("time: 0:00", cues)
        files = files_of(self.walk)
        self.assertGreater(len(files), 50)
        for name, text in files.items():
            for at, line in enumerate(text.split("\n")):
                self.assertNotIn(line.strip(), cues, f"{name}:{at + 1} is a private line of the class")
            try:
                self.assertEqual(private_lines(text), [], name)
            except MixedCue as mixed:
                self.fail(f"{name}: {mixed}")
            if name.endswith(".toml"):
                self.assertEqual(toml_cues(text), [], name)
        # What students keep: a public line next to a cue in the class notes
        self.assertIn("A project needs a place for its code, a command to run,", files["notes.md"])
        self.assertIn("$ rm build/top.txt; just setup; ls build", files["notes.md"])

    def test_second_run_changes_nothing(self) -> None:
        head = git(self.walk, "rev-parse", "HEAD")
        again = self.walk_update("--repo", str(self.repo))
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("has no changes", again.stdout)
        self.assertNotIn("edited by hand", again.stdout)
        self.assertEqual(git(self.walk, "status", "--porcelain", "--untracked-files=all"), "")
        self.assertEqual(git(self.walk, "rev-parse", "HEAD"), head)

    def test_the_old_sites_go(self) -> None:
        "Over the layout of before, with a website for each walk in sites/ID/, walk-update removes the files that it made there, and keeps the rest."
        clone = self.walk_clone("old-sites")
        made = {"sites/tests/_smalldocs.yml": f"# {render.MADE}\n", "sites/tests/styles.css": f"/* {render.MADE} */\n",
                "sites/tests/index.qmd": f"<!-- {render.MADE} -->\n", "sites/tests/read/step-01.qmd": f"<!-- {render.MADE} -->\n",
                "sites/gone/build/step-02.qmd": f"<!-- {render.MADE} -->\n"}
        mine = {"sites/tests/notes.qmd": "Mine.\n", "sites/own.css": "/* mine */\n"}
        for name, text in {**made, **mine}.items():
            (clone / name).parent.mkdir(parents=True, exist_ok=True)
            (clone / name).write_text(text)
        git(clone, "add", "-A")
        git(clone, "commit", "--quiet", "-m", "The websites of before")
        done = self.walk_update("--repo", str(self.repo), walk=clone)
        self.assertEqual(done.returncode, 0, done.stderr)
        for name in made:
            self.assertFalse((clone / name).exists(), name)
        for name, text in mine.items():
            self.assertEqual((clone / name).read_text(), text, name)
        self.assertFalse((clone / "sites" / "gone").exists(), "a folder that held only made files goes")
        self.assertFalse((clone / "sites" / "tests" / "read").exists())
        self.assertTrue((clone / "site" / "tests" / "index.qmd").is_file())

    def test_walk_update_after_just_pages(self) -> None:
        "just pages removes an old page of render.py and leaves it uncommitted; walk-update then runs. A file of the author that is gone still stops it."
        clone = self.walk_clone("after-pages")
        (clone / "sites" / "old").mkdir(parents=True)
        (clone / "sites" / "old" / "index.qmd").write_text(f"<!-- {render.MADE} -->\n")
        (clone / "mine.txt").write_text("Mine.\n")
        git(clone, "add", "-A")
        git(clone, "commit", "--quiet", "-m", "An old page, and a file of the author")
        pages = self.walk_update("--repo", str(self.repo), "--pages-only", walk=clone)
        self.assertEqual(pages.returncode, 0, pages.stderr)
        self.assertFalse((clone / "sites" / "old" / "index.qmd").exists())
        done = self.walk_update("--repo", str(self.repo), walk=clone)
        self.assertEqual(done.returncode, 0, done.stderr)
        git(clone, "reset", "--quiet", "--hard")
        (clone / "mine.txt").unlink()
        refused = self.walk_update("--repo", str(self.repo), walk=clone)
        self.assertEqual(refused.returncode, 2, refused.stdout)
        self.assertIn("mine.txt", refused.stderr)

    def test_a_theme_comes_and_goes(self) -> None:
        """A class's site.toml gives the walk repository the theme's files in site/_extensions/, through just pages and then
        walk-update. Without site.toml, the next run removes them, and the walk repository is as it was before the theme."""
        theme = self.tmp / "github" / "o" / "demo.git"   # o/demo, which git finds here instead of on GitHub
        (theme / "_extensions" / "demo").mkdir(parents=True)
        (theme / "_extensions" / "demo" / "smalldocs.yml").write_text("css: demo.css\n")
        (theme / "_extensions" / "demo" / "demo.css").write_text("body { color: red; }\n")
        (theme / "_extensions" / "demo" / "font.woff").write_bytes(bytes(range(256)))
        git(theme.parent, "init", "-q", "-b", "main", str(theme))
        git(theme, "add", "-A")
        git(theme, "-c", "user.name=t", "-c", "user.email=t@e", "commit", "-qm", "v1")
        git(theme, "tag", "v1")
        folder = self.tmp / "themed-class"
        shutil.copytree(self.folder, folder, ignore=shutil.ignore_patterns(".git"))
        clone = self.walk_clone("themed-walk")
        before = files_of(clone)

        def update(*args: str) -> subprocess.CompletedProcess:
            env = {**self.env, "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": f"url.{(self.tmp / 'github').as_uri()}/.insteadOf",
                   "GIT_CONFIG_VALUE_0": "git@github.com:"}
            return script("walk_update.py", "--project", "tally", "--upstream", "o", "--toc", str(folder / "toc.toml"), "--walk", str(clone),
                          "--repo", str(self.repo), *args, cwd=folder, env=env)

        (folder / "site.toml").write_text('theme = "o/demo@v1"\n\n[smalldocs]\nreference-location = "margin"\n')
        for args in (["--pages-only"], []):   # just pages, then just walk-update over its uncommitted pages
            done = update(*args)
            self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual((clone / "site/_extensions/demo/font.woff").read_bytes(), bytes(range(256)))
        self.assertIn("commit:", (clone / "site/_extensions/demo/.source").read_text())
        self.assertIn('theme: "demo"', (clone / "site/_smalldocs.yml").read_text())
        git(clone, "add", "-A")
        git(clone, "commit", "--quiet", "-m", "The theme")
        css = clone / "site/_extensions/demo/demo.css"
        css.write_text("body { color: green; }\n")   # an edit by hand of a file of the theme
        refused = update()
        self.assertEqual(refused.returncode, 2, refused.stdout)
        self.assertIn("site/_extensions/demo/demo.css", refused.stderr)
        self.assertEqual(css.read_text(), "body { color: green; }\n")
        git(clone, "checkout", "--quiet", "--", ".")
        own = clone / "site/_extensions/mine.css"   # a file of the author's, committed, which a list edited by hand names
        own.write_text("p { margin: 0; }\n")
        git(clone, "add", "site/_extensions/mine.css")
        git(clone, "commit", "--quiet", "-m", "A file of mine")
        listed = clone / "site/_extensions/.walk-kit"
        listed.write_text(listed.read_text() + "site/_extensions/mine.css\n")
        (folder / "site.toml").unlink()
        for args in (["--pages-only"], []):
            done = update(*args)
            self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(own.read_text(), "p { margin: 0; }\n", "a file that the list of the last commit does not name stays")
        own.unlink()
        git(clone, "commit", "--quiet", "-am", "Not mine after all")
        self.assertEqual([p for p in (clone / "site" / "_extensions").rglob("*") if p.is_file()], [], "no file of the theme is left")
        self.assertEqual(files_of(clone), before)
        self.assertFalse([name for name in files_of(folder) if "_extensions" in name or name.endswith(".source")], "nothing of the theme in the class")

    def test_walk_update_twice_without_a_commit(self) -> None:
        "A walk-update that commits nothing leaves the justfile as the template has it, and a second walk-update runs; an edit by hand still stops it."
        clone = self.walk_clone("twice")
        justfile = clone / "justfile"
        older = git(KIT, "show", "HEAD:templates/walk/justfile")   # the walk repository of an older walk-kit, with no site recipe
        if "\nsite *args:" in older:
            self.skipTest("walk-kit's last commit has the site recipe: no older justfile to start from")
        for key, value in VALUES.items():
            older = older.replace(f"@{key}@", value)
        justfile.write_text(older + "\n")
        git(clone, "commit", "--quiet", "-am", "An older justfile")
        (clone / "walk.md").write_text("# The notes of before toc.toml\n")   # the first run removes it, and the second must not mind
        git(clone, "add", "walk.md")
        git(clone, "commit", "--quiet", "-m", "walk.md of before")
        (clone / "repo").mkdir()
        os.mkfifo(clone / "repo" / "pipe")   # what the trial run leaves out of its copy
        for _ in range(2):
            done = self.walk_update("--repo", str(self.repo), "--no-commit", walk=clone)
            self.assertEqual(done.returncode, 0, done.stderr)
        self.assertFalse((clone / "walk.md").exists())
        self.assertIn("\nsite *args:", justfile.read_text())
        justfile.write_text(justfile.read_text() + "\n# mine\n")
        refused = self.walk_update("--repo", str(self.repo), "--no-commit", walk=clone)
        self.assertEqual(refused.returncode, 2, refused.stdout)
        self.assertIn("justfile", refused.stderr)
        self.assertNotIn("walk-update-", refused.stderr, "the walk repository's paths, and not the trial's copy")
        git(clone, "checkout", "--quiet", "--", "justfile")
        mine = clone / "mine.md"
        mine.write_text(f"<!-- {render.MADE} -->\nMine.\n")   # the line of render.py, in a file of the author, staged
        git(clone, "add", "mine.md")
        refused = self.walk_update("--repo", str(self.repo), "--no-commit", walk=clone)
        self.assertEqual(refused.returncode, 2, refused.stdout)
        self.assertIn("staged", refused.stderr)
        self.assertIn("mine.md", git(clone, "diff", "--cached", "--name-only"), "the author's staging stays")

    def test_copies_left_by_no_commit(self) -> None:
        "The notes that a walk-update --no-commit copied from the class stay uncommitted, and the next walk-update runs. A hand edit of the copy stops it."
        folder = self.tmp / "notes-class"
        shutil.copytree(self.folder, folder, ignore=shutil.ignore_patterns(".git"))
        clone = self.walk_clone("notes-walk")
        (folder / "notes.md").write_text((folder / "notes.md").read_text() + "\nA line for students.\n")

        def update() -> subprocess.CompletedProcess:
            return script("walk_update.py", "--project", "tally", "--upstream", "o", "--toc", str(folder / "toc.toml"), "--walk", str(clone),
                          "--repo", str(self.repo), "--no-commit", cwd=folder, env=self.env)

        for _ in range(2):
            done = update()
            self.assertEqual(done.returncode, 0, done.stderr)
        copied = next(name for name in git(clone, "status", "--porcelain").split("\n") if name.endswith("notes.md"))[3:]
        (clone / copied).write_text((clone / copied).read_text() + "\nMine.\n")
        refused = update()
        self.assertEqual(refused.returncode, 2, refused.stdout)
        self.assertIn("would not write as they are", refused.stderr)
        self.assertIn(copied, refused.stderr)
        self.assertIn("Mine.", (clone / copied).read_text(), "nothing is written")

    def test_old_templates_replaced_hand_edits_kept(self) -> None:
        if not (KIT / ".git").exists():
            self.skipTest("walk-kit is not a git clone, so it knows no old template")
        # The first walk-kit pinned timewalk with timewalk := "...@v1.0.1"; a later one took it from the branch walks
        for commit, source in (("c6312d7", "git+https://github.com/rahuldave/timewalk@v1.0.1"),
                               ("5371e76", "git+https://github.com/rahuldave/timewalk@walks")):
            with self.subTest(commit=commit):
                clone = self.walk_clone(f"walk-{commit}")
                old = git(KIT, "show", f"{commit}:templates/walk/justfile") + "\n"
                for key, value in {**VALUES, "timewalk": source}.items():
                    old = old.replace(f"@{key}@", value)
                self.assertNotEqual(old, fill("walk/justfile", VALUES))
                (clone / "justfile").write_text(old)
                readme = (clone / "README.md").read_text() + "\nA line that the teacher wrote by hand.\n"
                (clone / "README.md").write_text(readme)
                git(clone, "commit", "--quiet", "-am", "An old walk repository, and an edit by hand")
                done = self.walk_update(walk=clone)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual((clone / "justfile").read_text(), fill("walk/justfile", VALUES), "the old justfile stays")
                self.assertEqual((clone / "README.md").read_text(), readme)
                self.assertIn("README.md matches no version of walk-kit's template", done.stdout)
                self.assertIn("kept README.md as edited by hand", done.stdout)
                self.assertNotIn("justfile matches no version", done.stdout)
                self.assertIn(f"took timewalk from {source}. It now takes timewalk from {GITHUB}", done.stdout)
                git(clone, "commit", "--quiet", "-am", "walk_update")
        replaced = self.walk_update("--replace-edited", walk=clone)
        self.assertEqual(replaced.returncode, 0, replaced.stderr)
        self.assertEqual((clone / "README.md").read_text(), fill("walk/README.md", VALUES))

    def test_walk_justfile_lists_its_recipes(self) -> None:
        done = just(self.walk, "--list", env=self.env)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(re.findall(r"^\s+(\S+)", done.stdout, re.MULTILINE), ["pdf", "present", "setup", "site"])

    def offline(self) -> dict:  # The environment of a student with no network: github.com is a folder of bare clones
        "Keep git off the network: https is not allowed, and https://github.com/ leads to a folder of the temporary folder."
        github = self.tmp / "github"
        if not (github / "o" / "tally.git").exists():
            git(self.tmp, "clone", "--quiet", "--bare", str(self.repo), str(github / "o" / "tally.git"))
        return {**self.env, "GIT_ALLOW_PROTOCOL": "file", "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": f"url.file://{github}/.insteadOf",
                "GIT_CONFIG_VALUE_0": "https://github.com/", "UV_OFFLINE": "1"}

    def test_walk_setup_clones_the_upstream(self) -> None:
        env, walk = self.offline(), self.walk_clone("walk-setup")
        git(walk, "remote", "set-url", "origin", "https://github.com/me/tally-walk.git")   # the student's fork, with no fork of tally
        done = just(walk, "setup", env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(git(walk / "repo", "remote", "get-url", "origin"), "https://github.com/o/tally.git")
        self.assertEqual(git(walk / "repo", "remote", "get-url", "upstream"), "https://github.com/o/tally.git")
        self.assertIn("with 7 steps from o/tally", done.stdout)
        self.assertEqual(git(walk, "status", "--porcelain"), "", "repo/ must be ignored")
        # A tag that moved upstream moves in repo/ at the next just setup
        upstream = self.tmp / "github" / "o" / "tally.git"
        moved = git(upstream, "rev-parse", "step-02^{commit}")
        git(upstream, "tag", "-f", "-a", "step-01", "-m", "step-01: moved", moved)
        try:
            done = just(walk, "setup", env=env)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(git(walk / "repo", "rev-parse", "step-01^{commit}"), moved)
        finally:
            shutil.rmtree(upstream)

    def test_walk_setup_without_the_network(self) -> None:
        env, walk = self.offline(), self.walk_clone("walk-no-network")
        cut = {**env, "GIT_CONFIG_VALUE_0": "https://github.com/", "GIT_CONFIG_KEY_0": "url.https://offline.invalid/.insteadOf"}
        # A first clone with no network fails, and says why
        done = just(walk, "setup", env=cut)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("setup: could not clone https://github.com/o/tally.git. Check the network", done.stderr)
        self.assertFalse((walk / "repo").exists())
        # After one setup, a setup with no network keeps the tags of repo/, and goes on to just present
        self.assertEqual(just(walk, "setup", env=env).returncode, 0)
        done = just(walk, "setup", env=cut)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("setup: could not fetch from GitHub; using the tags you have", done.stderr)
        self.assertIn("with 7 steps from o/tally", done.stdout)
        # A path cloned with no network has the tags of the path, but not of GitHub: setup fails, and says why
        path = self.walk_clone("walk-no-network-path")
        done = just(path, "setup", str(self.repo), env=cut)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("setup: could not fetch the tags of the steps from GitHub", done.stderr)

    def test_walk_setup_clones_a_fork(self) -> None:
        env, walk = self.offline(), self.walk_clone("walk-fork")
        git(walk, "remote", "set-url", "origin", "git@github.com:me/tally-walk.git")
        fork = self.tmp / "github" / "me" / "tally.git"
        git(self.tmp, "clone", "--quiet", "--bare", str(self.repo), str(fork))
        git(fork, "tag", "-d", *git(fork, "tag").split())   # a fork without the tags: they come from the upstream
        done = just(walk, "setup", env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(git(walk / "repo", "remote", "get-url", "origin"), "https://github.com/me/tally.git")
        self.assertEqual(len(git(walk / "repo", "tag", "-l", "step-*").split()), 7)

    def test_walk_setup_takes_a_path(self) -> None:
        env, walk = self.offline(), self.walk_clone("walk-path")
        done = just(walk, "setup", str(self.repo), env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(git(walk / "repo", "remote", "get-url", "origin"), str(self.repo))

    def test_walk_justfile_guards(self) -> None:
        env = self.offline()
        one = self.walk_clone("walk-one", self.walk_commits[-1])   # as walk_init made it: walk.md and no toc.toml
        done = just(one, "pdf", env=env)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("this walk has no slides", done.stderr)
        done = just(one, "pdf", "tests", env=env)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("this repository has one walk", done.stderr)
        done = just(one, "present", "tests", env=env)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("this repository has one walk", done.stderr)
        many = self.walk_clone("walk-bare")
        (many / "toc.toml").write_text('[[walk]]\nid = "bare"\ntitle = "No slides"\nkind = "narrative"\nnotes = "notes.md"\n')
        done = just(many, "pdf", env=env)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("walk bare has no slides", done.stderr)
        self.assertFalse((many / "build" / "walk.pdf").exists())


class Templates(unittest.TestCase):
    "The templates, filled as class_init and walk_init fill them."

    def filled(self) -> dict[str, str]:  # Each template by its path under templates/, filled with the values of its script
        "Fill every template with the values that its script gives it."
        values = {"walk": VALUES, "class": {**VALUES, "repo_default": '"/tmp/tally"', "walk_default": '"/tmp/tally-walk"'}}
        return {path.relative_to(KIT / "templates").as_posix(): fill(path.relative_to(KIT / "templates").as_posix(),
                                                                       values["class" if path.parent.name == "class" else "walk"])
                for path in sorted((KIT / "templates").rglob("*")) if path.is_file()}

    def test_every_key_is_given(self) -> None:
        given = {"walk": set(VALUES), "class": set(VALUES) | {"repo_default", "walk_default"}}
        used = {template: "class" for template in class_init.FILES.values()} | {template: "walk" for template in walk_init.FILES.values()}
        used |= {"class/notes-preamble.md": "class", "class/toc.toml": "class"}
        for path in (KIT / "templates").rglob("*"):
            if path.is_file():
                name = path.relative_to(KIT / "templates").as_posix()
                self.assertIn(name, used, f"no script fills templates/{name}")
                keys = {key.strip("@") for key in KEY.findall(path.read_text())}
                self.assertLessEqual(keys, given[used[name]], name)

    def test_toml_and_justfiles_parse(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            for name, text in self.filled().items():
                if name.endswith(".toml"):
                    tomllib.loads(text)
                if name.endswith("justfile") and shutil.which("just"):
                    (Path(scratch) / "justfile").write_text(text)
                    done = subprocess.run(["just", "--justfile", str(Path(scratch) / "justfile"), "--summary"], capture_output=True, text=True,
                                          check=False)
                    self.assertEqual(done.returncode, 0, f"{name}: {done.stderr}")

    @unittest.skipUnless(shutil.which("uvx"), "uvx is not on this machine")
    def test_workflows_pass_actionlint(self) -> None:
        workflows = {name: text for name, text in self.filled().items() if name.endswith((".yml", ".yaml"))}
        self.assertIn("walk/pages.yml", workflows)
        with tempfile.TemporaryDirectory() as scratch:
            folder = Path(scratch) / ".github" / "workflows"
            folder.mkdir(parents=True)

            def lint(text: str) -> subprocess.CompletedProcess:  # What actionlint said
                (folder / "pages.yml").write_text(text)
                return subprocess.run(["uvx", "--from", "actionlint-py", "actionlint", str(folder / "pages.yml")], capture_output=True,
                                      text=True, cwd=scratch, check=False)

            for name, text in workflows.items():
                done = lint(text)
                self.assertEqual(done.returncode, 0, f"{name}: {done.stdout}{done.stderr}")
            # actionlint does read the file: a step that is not there fails it
            broken = lint(workflows["walk/pages.yml"].replace("steps.site.outputs.pages }}", "steps.nosuch.outputs.pages }}", 1))
            self.assertNotEqual(broken.returncode, 0)


class Private(unittest.TestCase):
    "What private.py promises: the lines for the presenter go, and every other line stays as it was."

    def test_cues_and_their_blockquote(self) -> None:
        text = "Intro.\n\n> We start.\n> Say: hello\ngoes on\n>\n> more\n\nAfter.\n"
        self.assertEqual(public(text), "Intro.\n\nAfter.\n")

    def test_forms_of_a_cue(self) -> None:
        for line in ("> Say: x", "  > Say: x", "> say: x", "> NOTE: x", "> **Say:** x", "> **Note**: x", "> Say : x", "> > Note: x",
                     "- > Say: x", "- - > Say: x", "- [ ] > Say: x", "1. > Note: x", "<!-- > Say: x -->", "time: 1:23", "   time: 12:05 "):
            with self.subTest(line=line):
                self.assertEqual(private_lines(f"a\n\n{line}\n\nb"), [2])

    def test_public_lines_stay(self) -> None:
        for line in ("> Note that x", "> Notes: x", "> Try: x", "> Saying x", "Say: x", "time: soon", "time: 1:2"):
            with self.subTest(line=line):
                self.assertEqual(private_lines(f"a\n\n{line}\n\nb"), [])

    def test_a_new_block_ends_the_blockquote(self) -> None:
        for line in ("## step-02 Next", "$ just test", "do$ uv lock", "runs$ uv run train", "patch$ src/a.py", "::: do", ":::", "- an item",
                     "```", "<div>"):
            with self.subTest(line=line):
                self.assertEqual(private_lines(f"> Say: x\n{line}\n"), [0])

    def test_comment_keeps_its_end(self) -> None:
        self.assertEqual(public("a\n<!--\n> Say: x\n-->\nb"), "a\n<!--\n-->\nb")
        self.assertEqual(public("a\n<!--\n> Say: x -->\nb"), "a\n<!--\n-->\nb")

    def test_fenced_code_stays(self) -> None:
        text = "a\n```\n> Say: x\ntime: 1:00\n```\nb\n~~~~\n> Note: y\n~~~\nstill code\n~~~~\n"
        self.assertEqual(private_lines(text), [])
        self.assertEqual(public(text), text)
        self.assertEqual(in_code(text), [2, 3, 7])
        # Not a fence: a backtick after the backticks, or four spaces before them
        self.assertEqual(private_lines("```a`b\n> Say: x\n"), [1])
        self.assertEqual(private_lines("    ```\n> Say: x\n"), [1])
        self.assertEqual(fenced(["```", "x", "~~~", "````", "y"]), {0, 1, 2, 3})

    def test_mixed_cue_refused(self) -> None:
        with self.assertRaises(MixedCue) as raised:
            private_lines("> Say: x\n> Try: y\n")
        self.assertEqual((raised.exception.at, raised.exception.cue), (1, 0))
        self.assertEqual(public("> Say: x\n\n> Try: y\n"), "> Try: y\n")

    def test_one_blank_line_goes_with_a_run(self) -> None:
        self.assertEqual(public("a\n\ntime: 1:00\n\nb\n"), "a\n\nb\n")
        self.assertEqual(public("time: 1:00\n\nb\n"), "b\n")
        self.assertEqual(public("a\ntime: 1:00\nb\n"), "a\nb\n")
        self.assertEqual(public("a\n\n> Say: x\n\nb", start=2), "b")

    def test_toml_cues(self) -> None:
        text = "# Say: hi\n# > Note: x\n  # time: 1:00\n# Saying\n# Try: y\nkey = 1 # Say: not a comment line\n"
        self.assertEqual(toml_cues(text), [0, 1, 2])


def pdf_of(
    lines: list[str],  # The lines of text of its one page
) -> bytes:  # A PDF that pdftotext reads
    "Make a PDF of one page of text, with nothing but the standard library."
    shown = " ".join("(" + line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ") Tj T*" for line in lines)
    stream = f"BT /F1 10 Tf 14 TL 40 800 Td {shown} ET".encode()
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
               b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"]
    out, offsets = b"%PDF-1.4\n", []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode() + b"".join(f"{at:010d} 00000 n \n".encode() for at in offsets)
    return out + f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()


class PdfCheck(unittest.TestCase):
    "What pdf_check.py promises: the last words of each Markdown slide are in the PDF, and a slide cut off is reported."

    SLIDES = "# Counting\n\nWe count the words of a text\n\n```\nprint('code is skipped')\n```\n$ just test\n---\n# Two\n\n- the last words are here\n"

    def test_last_words(self) -> None:
        self.assertEqual(pdf_check.last_words(self.SLIDES.split("\n---\n")[0], 3), "of a text")
        self.assertEqual(pdf_check.last_words("- **Bold** item, then [a link](http://x)\n", 4), "item, then a link")
        self.assertEqual(pdf_check.last_words("| a | b |\n|---|:-:|\n| c | `d` |\n", 6), "c d")
        self.assertIsNone(pdf_check.last_words("![a picture](a.svg)\n", 6))

    def test_slides_of(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            (Path(scratch) / "a.md").write_text("one\n---\ntwo\n---\nthree")
            self.assertEqual(pdf_check.slides_of(Path(scratch), "a.md#2"), ["two"])
            self.assertEqual(pdf_check.slides_of(Path(scratch), "a.md#2-3"), ["two", "three"])
            self.assertEqual(len(pdf_check.slides_of(Path(scratch), "a.md")), 3)
            self.assertEqual(pdf_check.slides_of(Path(scratch), "pictures/a.svg"), [])

    def check(
        self,
        lines: list[str],  # The text of the PDF
        *args: str,  # More arguments
        toc: bool = False,  # Make a class with toc.toml, whose second walk has the slides
    ) -> subprocess.CompletedProcess:  # What pdf_check printed, and its exit code
        "Run pdf_check on a PDF of these lines, in a class with one slides file of two slides and a picture."
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        slides = folder / ("walks/b/slides" if toc else "slides")
        slides.mkdir(parents=True)
        (slides / "a.md").write_text(self.SLIDES)
        (slides / "slides.toml").write_text('[slides]\nstep-01 = ["a.md"]\nstep-02 = ["a.svg"]\n')
        if toc:
            (folder / "toc.toml").write_text('[[walk]]\nid = "a"\nnotes = "notes.md"\n\n[[walk]]\nid = "b"\nfolder = "walks/b"\n')
        (folder / "out.pdf").write_bytes(pdf_of(lines))
        return script("pdf_check.py", "out.pdf", "--class", str(folder), *args, cwd=folder)

    @unittest.skipUnless(shutil.which("pdftotext") and shutil.which("pdfinfo"), "pdftotext is not on this machine")
    def test_whole_and_cut(self) -> None:
        whole = ["Counting", "We count the words of a text", "Two", "the last words are here"]
        done = self.check(whole)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("slides with text checked: 2; last words missing from the PDF: 0", done.stdout)
        self.assertIn("1 pages", done.stdout)
        cut = self.check(whole[:3] + ["the last words"])
        self.assertEqual(cut.returncode, 1)
        self.assertIn("MISSING at step-01 / a.md: [# Two] ... the last words are here", cut.stdout)
        self.assertEqual(self.check(whole, "--walk", "b", toc=True).returncode, 0)
        self.assertEqual(self.check(whole[:3], "--walk", "b", toc=True).returncode, 1)

    def test_refusals(self) -> None:
        done = self.check([], "--walk", "b")
        self.assertEqual(done.returncode, 2)
        self.assertIn("has no toc.toml", done.stderr)
        done = self.check([], "--walk", "a", toc=True)
        self.assertEqual(done.returncode, 2)
        self.assertIn("walk a has no slides manifest", done.stderr)


class StyleSync(unittest.TestCase):
    "What style_sync.py promises: it says whether walk-kit's copies match nossaifd's, and copies them with --write."

    def setUp(self) -> None:
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.kit, self.theirs = self.tmp / "kit", self.tmp / "nossaifd"
        (self.kit / "scripts").mkdir(parents=True)
        for name in ("style_sync.py", "style.py", "common.py", "private.py"):
            shutil.copy(SCRIPTS / name, self.kit / "scripts" / name)
        (self.kit / "style").mkdir()
        (self.kit / "style" / "README.md").write_text("Copies from nossaifd, at its\ncommit 0000000.\nIts site is there.\n")
        self.theirs.mkdir()
        for folder, words in ((self.kit / "style", "old"), (self.theirs, "new")):
            (folder / "GUIDE.md").write_text(f"# The {words} guide\n")
            (folder / "check.py").write_text(f"print('{words}')\n")
        git(self.theirs, "init", "--quiet")
        git(self.theirs, "add", "-A")
        git(self.theirs, "commit", "--quiet", "-m", "guide")
        self.commit = git(self.theirs, "rev-parse", "--short", "HEAD")

    def sync(self, *args: str) -> subprocess.CompletedProcess:  # What style_sync printed, and its exit code
        "Run the copy of style_sync.py, with nossaifd in the temporary folder."
        return subprocess.run([sys.executable, str(self.kit / "scripts" / "style_sync.py"), *args], capture_output=True, text=True,
                              env={**ENV, "NOSSAIFD": str(self.theirs)}, check=False)

    def test_differ_then_write_then_match(self) -> None:
        done = self.sync()
        self.assertEqual(done.returncode, 1, done.stderr)
        self.assertIn("style/GUIDE.md, style/check.py differ", done.stdout)
        self.assertEqual((self.kit / "style" / "GUIDE.md").read_text(), "# The old guide\n")
        done = self.sync("--write")
        self.assertEqual(done.returncode, 0, done.stderr)
        for name in ("GUIDE.md", "check.py"):
            self.assertEqual((self.kit / "style" / name).read_bytes(), (self.theirs / name).read_bytes())
        self.assertEqual((self.kit / "style" / "README.md").read_text(), f"Copies from nossaifd, at its\ncommit {self.commit}.\nIts site is there.\n")
        done = self.sync()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(f"match nossaifd at {self.commit}", done.stdout)

    def test_from_github_without_a_clone(self) -> None:
        spec = importlib.util.spec_from_file_location("style_sync_copy", self.kit / "scripts" / "style_sync.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        asked = []

        def answer(url: str, timeout: float) -> mock.MagicMock:  # A reply from GitHub with nossaifd's file
            asked.append(url)
            reply = mock.MagicMock()
            reply.__enter__.return_value.read.return_value = (self.theirs / url.rsplit("/", 1)[1]).read_bytes()
            return reply

        with mock.patch.object(module, "nossaifd", lambda: None), mock.patch("urllib.request.urlopen", answer), \
                mock.patch.object(sys, "argv", ["style_sync.py", "--write"]), mock.patch("builtins.print"):
            self.assertEqual(module.main(), 0)
        self.assertEqual(asked, [module.RAW + "GUIDE.md", module.RAW + "check.py"])
        self.assertTrue(all(url.startswith("https://raw.githubusercontent.com/rahuldave/nossaifd/main/") for url in asked))
        self.assertEqual((self.kit / "style" / "GUIDE.md").read_text(), "# The new guide\n")
        self.assertIn("at its\ncommit main.", (self.kit / "style" / "README.md").read_text())


if __name__ == "__main__":
    unittest.main()
