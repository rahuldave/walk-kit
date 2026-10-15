"""Tests of pyproject.toml and uv.lock in Build it yourself: git check compares them as data, as timewalk does, a patch$ line
of a pyproject.toml sets its values with tomlkit, and only uv changes dependencies and uv.lock.

    python3 -m unittest tests.test_toml

They need uv. The test of package_names against timewalk's own runs timewalk through uvx, from TIMEWALK or GitHub.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import follow
import package_names
import render
from test_render import Case, commit, sh
from test_review import TIMEWALK_TEST

TIMEWALK = os.environ.get("TIMEWALK", "git+https://github.com/rahuldave/timewalk")
LOOSE = ["pyproject.toml", "uv.lock"]
START = '[project]\nname = "demo"\nversion = "0.1.0"\nrequires-python = ">=3.11"\ndependencies = []\n'
DEV = '\n[dependency-groups]\ndev = [\n    "ruff>=0.17.0",\n]\n'
RUFF = '\n[tool.ruff]\nline-length = 100\n'


def lock(
    ruff: str,  # The version of ruff that uv add found
    more: str = "",  # More packages, as uv.lock writes them
) -> str:  # A uv.lock of the demo project with ruff in its group dev, as uv lock writes it
    "Write the uv.lock that uv add --dev ruff writes on the day that ruff has this version."
    return ('version = 1\nrequires-python = ">=3.11"\n\n[[package]]\nname = "demo"\nversion = "0.1.0"\nsource = { virtual = "." }\n\n'
            '[package.dev-dependencies]\ndev = [\n    { name = "ruff" },\n]\n\n[package.metadata]\n\n[package.metadata.requires-dev]\n'
            f'dev = [{{ name = "ruff", specifier = ">={ruff}" }}]\n\n[[package]]\nname = "ruff"\nversion = "{ruff}"\n'
            f'source = {{ registry = "https://pypi.org/simple" }}\n{more}')


def file_of(
    path: str,  # A file of a move
    by: object,  # "patch", or the index of the do$ line that writes it
    patch: str | None,  # What is changed by hand, from its first hunk
) -> dict:  # The file, as the facts have it
    "Make a modified file of the facts."
    return {"path": path, "old_path": None, "status": "modified", "added": 1, "removed": 0, "binary": False, "diff": patch or "",
            "names": {"added": [], "removed": [], "changed": []}, "by": by, "patch": patch}


def tutorial(
    loose: list[str],  # The walk's loose
    start: str,  # The commit before the move
    sha: str,  # The move's commit
    parts: list[dict],  # The move's text
    files: list[dict],  # The move's files
) -> tuple[dict, dict]:  # The facts of a tutorial of one stop with this one move, and the stop
    "Make the facts of a tutorial whose do$ lines ran."
    move = {"name": "step-03.2", "number": "3.2", "title": "A line length", "commit": sha, "parts": parts, "files": files}
    stop = {"name": "step-03", "number": "3", "title": "ruff", "start": start, "commit": sha, "parts": [], "files": [], "moves": [move]}
    return {"walk": {"kind": "tutorial", "loose": loose, "github": "https://github.com/o/demo"}, "observed": True, "stops": [stop],
            "history": {}, "intro": []}, stop


def hunks(
    old: str,  # A file before
    new: str,  # The same file after
) -> str:  # The diff of the two, from its first hunk, as the facts' patch has it
    "Diff two texts as git does, and drop the header."
    with tempfile.TemporaryDirectory() as scratch:
        (Path(scratch) / "a").write_text(old)
        (Path(scratch) / "b").write_text(new)
        out = subprocess.run(["git", "diff", "--no-index", "a", "b"], cwd=scratch, capture_output=True, text=True).stdout
    return out[out.index("@@"):]


def needs_uv(case: unittest.TestCase) -> None:
    "Skip a test that runs uv, where uv is missing."
    if not shutil.which("uv"):
        case.skipTest("uv is not installed")


class PackageNames(unittest.TestCase):
    "walk-kit's package_names gives what timewalk's gives, on every pyproject.toml and uv.lock of tally, and on odd cases."

    EDGES = {
        "pyproject.toml": [
            START.replace("[]", '["Uvicorn[Standard , http2] >= 0.30 ; python_version < \'3.12\'", "x @ git+https://e.com/x@v1", "Typing_Extensions"]')
            + '\n[project.optional-dependencies]\nplot = ["matplotlib>=3.8", "numpy[dev]~=2.0"]\n'
            + '\n[dependency-groups]\ntest = ["pytest>=8"]\ndev = [{ include-group = "test" }, "ruff>=0.17"]\n'
            + '\n[build-system]\nrequires = ["hatchling>=1.25"]\nbuild-backend = "hatchling.build"\n'
            + '\n[tool.uv]\ndev-dependencies = ["mypy==1.0"]\n\n[tool.uv.sources]\ntalib = { workspace = true }\n'
            + '\n[tool.uv.workspace]\nmembers = ["packages/*"]\n\n[tool.ruff]\nline-length = 100\n',
            "[project\nbroken",
        ],
        "uv.lock": [
            lock("0.17.0", '\n[[package]]\nname = "talib"\nversion = "0.1.0"\nsource = { editable = "packages/talib" }\n'
                 'dependencies = [\n    { name = "six", marker = "python_version < \'3.12\'" },\n]\n'
                 '\n[package.optional-dependencies]\nplot = [\n    { name = "numpy" },\n]\n'
                 '\n[[package]]\nname = "six"\nversion = "1.16.0"\nsource = { registry = "https://pypi.org/simple" }\n')
            + '\n[manifest]\nmembers = [\n    "demo",\n    "talib",\n]\n',
        ],
    }

    @staticmethod
    def files_of_tally() -> list[tuple[str, str]]:  # Each pyproject.toml and uv.lock of every commit of tally, once, with its path
        "Read tally's files of packages at every commit of every branch and tag."
        repo = TIMEWALK_TEST / "repo"
        listed = subprocess.run(["git", "-C", str(repo), "rev-list", "--all"], capture_output=True, text=True, check=True).stdout.split()
        found = {}
        for sha in listed:
            tree = subprocess.run(["git", "-C", str(repo), "ls-tree", "-r", "-z", sha], capture_output=True, text=True, check=True).stdout
            for entry in filter(None, tree.split("\0")):
                info, path = entry.split("\t", 1)
                if path.rsplit("/", 1)[-1] in ("pyproject.toml", "uv.lock"):
                    found[info.split()[2]] = path
        return [(path, subprocess.run(["git", "-C", str(repo), "cat-file", "blob", blob], capture_output=True, text=True, check=True).stdout)
                for blob, path in found.items()]

    def test_same_as_timewalk(self) -> None:
        "Every file of tally, and each odd case, reads the same through both, as JSON."
        if not shutil.which("uvx"):
            self.skipTest("uvx is not installed")
        if not (TIMEWALK_TEST / "repo" / ".git").exists():
            self.skipTest(f"{TIMEWALK_TEST}/repo is missing; run just build in timewalk-test, or set TIMEWALK_TEST")
        cases = self.files_of_tally()
        self.assertGreater(sum(path.endswith("uv.lock") for path, _ in cases), 3, "tally's uv.lock changes in several moves")
        cases += [(name, text) for name, texts in self.EDGES.items() for text in texts]
        program = ("import json, sys\nfrom timewalk import package_names\n"
                   "print(json.dumps([package_names(p, t.encode()) for p, t in json.load(sys.stdin)], sort_keys=True, default=str))")
        done = subprocess.run(["uvx", "--refresh-package", "timewalk", "--from", TIMEWALK, "python", "-c", program], input=json.dumps(cases),
                              capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        theirs = json.loads(done.stdout)
        ours = json.loads(json.dumps([package_names.package_names(p, t.encode()) for p, t in cases], sort_keys=True, default=str))
        for (path, _), mine, wanted in zip(cases, ours, theirs):
            self.assertEqual(mine, wanted, path)
        self.assertIsNone(ours[-2], "a file that is not TOML")

    def test_rules(self) -> None:
        "A requirement keeps its name, its extras, its address and its marker; a uv.lock keeps only the project's own packages."
        found = package_names.package_names("pyproject.toml", self.EDGES["pyproject.toml"][0].encode())
        self.assertEqual(found["project"]["dependencies"],
                         ["uvicorn[http2,standard]; python_version < '3.12'", "typing-extensions", "x @ git+https://e.com/x@v1"])   # sorted by repr, as timewalk does
        self.assertEqual(found["dependency-groups"]["dev"], ["ruff", {"include-group": "test"}])
        self.assertEqual(found["tool"]["ruff"], {"line-length": 100})
        newer = package_names.package_names("uv.lock", lock("0.17.1", '\n[[package]]\nname = "more"\nversion = "1.0"\n'
                                                                       'source = { registry = "https://pypi.org/simple" }\n').encode())
        self.assertEqual(newer, package_names.package_names("uv.lock", lock("0.17.0").encode()))


class CheckByData(Case):
    "git check compares pyproject.toml and uv.lock by package_names, through uv, with no uv lock --check."

    def setUp(self) -> None:
        "The project after uv add --dev ruff, on the day of ruff 0.17.0."
        super().setUp()
        needs_uv(self)
        self.sha = commit(self.repo, {"pyproject.toml": START + DEV, "uv.lock": lock("0.17.0")}, "ruff")

    def test_a_later_day(self) -> None:
        "ruff 0.17.1 in both files, and a new package that it needs in uv.lock: no difference."
        work = self.learner({"walk": {"loose": LOOSE}}, self.sha)
        (work / "pyproject.toml").write_text((START + DEV).replace("0.17.0", "0.17.1"))
        (work / "uv.lock").write_text(lock("0.17.1", '\n[[package]]\nname = "newdep"\nversion = "1.0"\nsource = { registry = "https://pypi.org/simple" }\n'))
        done = sh(work, f"git check {self.sha}", check=False)
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))
        self.assertNotIn("uv lock --check", "\n".join(render.check_lines({"walk": {"loose": LOOSE}})))

    def test_another_package(self) -> None:
        "A package of another name shows, in both files, line by line."
        work = self.learner({"walk": {"loose": LOOSE}}, self.sha)
        (work / "pyproject.toml").write_text((START + DEV).replace("ruff", "black"))
        (work / "uv.lock").write_text(lock("0.17.0").replace('"ruff"', '"black"'))
        found = sh(work, f"git check {self.sha}", check=False).stdout
        self.assertIn('-   "ruff"\n+   "black"', found)
        self.assertIn("uv.lock", found)
        self.assertNotIn("0.17.0", found)

    def test_other_tables_count(self) -> None:
        "Any other value of pyproject.toml counts, as in timewalk; a missing uv.lock shows."
        work = self.learner({"walk": {"loose": LOOSE}}, self.sha)
        (work / "pyproject.toml").write_text(START + DEV + RUFF)
        (work / "uv.lock").unlink()
        found = sh(work, f"git check {self.sha}", check=False).stdout
        self.assertIn('"line-length": 100', found)
        self.assertIn("deleted file mode", found)

    def test_without_loose(self) -> None:
        "Without loose, both files compare as text."
        work = self.learner({"walk": {"loose": []}}, self.sha)
        # another size: an edit of the same size in the second of the clone can look unchanged to git, which compares stat first
        (work / "pyproject.toml").write_text((START + DEV).replace("0.17.0", "0.17.10"))
        self.assertIn("pyproject.toml", sh(work, f"git check {self.sha}", check=False).stdout)

    def test_get_the_project(self) -> None:
        "follow reads each command of Get the project whole, the program's here-document too, and the page asks for no extra check."
        facts, _ = tutorial(LOOSE, self.sha, self.sha, [], [])
        page = "\n".join(render.clone_lines(facts, 2))
        commands = [command for block in follow.blocks_of(page) for command in block.commands]
        self.assertEqual(commands[3:], render.check_lines(facts))
        self.assertEqual(follow.checks_in(page), 0)
        self.assertIn("package_names.py", page)


class SetByData(Case):
    "A patch$ line of a pyproject.toml that loose names sets the commit's values with tomlkit, and keeps the student's uv add."

    def setUp(self) -> None:
        "The project after uv add --dev ruff (3.1), and after a line length for ruff (3.2), as in timewalk-test's tutorial."
        super().setUp()
        needs_uv(self)
        self.start = commit(self.repo, {"pyproject.toml": START + DEV + "\n[tool.black]\nline-length = 88\n", "uv.lock": lock("0.17.0")}, "ruff")
        self.sha = commit(self.repo, {"pyproject.toml": START + DEV + RUFF}, "line length")

    def page(
        self,
        facts: dict,  # The facts
        stop: dict,  # Its stop
    ) -> str:  # Build it yourself
        "Render the stop in Build it yourself, with the values that the pages set."
        facts["toml_edits"] = render.toml_edits(self.repo, facts)
        return "\n".join(render.stop_page(facts, stop, 1, "do", False))

    def run_page(
        self,
        work: Path,  # The learner's clone
        page: str,  # Build it yourself
        start: str,  # The first word of the command to run
    ) -> None:
        "Run the commands of the page that start so, as follow reads them."
        commands = [c for block in follow.blocks_of(page) for c in block.commands if c.startswith(start)]
        self.assertEqual(len(commands), 1, page)
        sh(work, commands[0])

    def test_the_tutorial(self) -> None:
        "The student's uv add wrote ruff>=0.17.1 on a later day; the command of 3.2 sets [tool.ruff], removes [tool.black], and git check passes."
        patch = hunks(START + DEV + "\n[tool.black]\nline-length = 88\n", START + DEV + RUFF)
        facts, stop = tutorial(LOOSE, self.start, self.sha, [{"kind": "patch", "mode": "shared", "path": "pyproject.toml"}],
                               [file_of("pyproject.toml", "patch", patch)])
        page = self.page(facts, stop)
        self.assertNotIn("git apply", page)
        self.assertNotIn("curl", page)
        work = self.learner(facts, self.start)
        mine = (START + DEV + "\n[tool.black]\nline-length = 88\n").replace("0.17.0", "0.17.1")
        (work / "pyproject.toml").write_text("# my notes\n" + mine)
        (work / "uv.lock").write_text(lock("0.17.1"))
        self.run_page(work, page, "uv run")
        text = (work / "pyproject.toml").read_text()
        self.assertIn('"ruff>=0.17.1"', text)
        self.assertIn("# my notes", text)
        self.assertNotIn("black", text)
        done = sh(work, f"git check {self.sha}", check=False)
        self.assertEqual((done.returncode, done.stdout), (0, ""))

    def test_after_uv_add(self) -> None:
        "A do$ line writes pyproject.toml, and a patch$ line adds [tool.uv]: the command sets only what the do$ line did not write."
        left = START + DEV   # what uv add --dev ruff writes, on the day of the commit
        after = left + '\n[tool.uv]\ndefault-groups = ["dev"]\n'
        sha = commit(self.repo, {"pyproject.toml": after}, "default groups")
        parts = [{"kind": "command", "text": "uv add --dev ruff", "makes": True, "mode": "shared", "track": "", "writes": ["pyproject.toml"]},
                 {"kind": "patch", "mode": "shared", "path": "pyproject.toml"}]
        facts, stop = tutorial(LOOSE, self.start, sha, parts, [file_of("pyproject.toml", 0, hunks(left, after))])
        self.assertEqual(render.toml_edits(self.repo, facts)[f"{sha}:pyproject.toml"],
                         ([(("tool", "uv"), {"default-groups": ["dev"]})], []))
        page = self.page(facts, stop)
        self.assertIn("After `uv add --dev ruff`, set the other values", page)
        work = self.learner(facts, self.start)
        (work / "pyproject.toml").write_text(left.replace("0.17.0", "0.17.1"))   # the do$ line, on a later day
        self.run_page(work, page, "uv run")
        self.assertEqual(sh(work, f"git check {sha}", check=False).stdout, "")

    def test_needs_the_project(self) -> None:
        "Without the project, the page cannot know the values, and says so."
        facts, stop = tutorial(LOOSE, self.start, self.sha, [{"kind": "patch", "mode": "shared", "path": "pyproject.toml"}],
                               [file_of("pyproject.toml", "patch", "@@ -1 +1 @@\n-a\n+b\n")])
        with self.assertRaises(render.PagesError) as caught:
            render.stop_page(facts, stop, 1, "do", False)
        self.assertIn("--repo", str(caught.exception))

    def test_watch_and_without_loose(self) -> None:
        "Read the tutorial says a patch; a walk whose loose does not name pyproject.toml patches its text."
        files = [file_of("pyproject.toml", "patch", "@@ -1 +1 @@\n-a\n+b\n")]
        parts = [{"kind": "patch", "mode": "shared", "path": "pyproject.toml"}]
        facts, stop = tutorial(LOOSE, self.start, self.sha, parts, files)
        self.assertIn("A patch to", "\n".join(render.stop_page(facts, stop, 1, "watch", False)))
        facts, stop = tutorial([], self.start, self.sha, parts, files)
        self.assertEqual(render.toml_edits(self.repo, facts), {})
        self.assertIn("git apply", "\n".join(render.stop_page(facts, stop, 1, "do", False)))

    def test_command(self) -> None:
        "The command names the file, writes each value as Python, and its here-document ends where follow ends it."
        lines = render.set_command("packages/a b/pyproject.toml", [(("tool", "x"), {"when": "PY", "on": True, "n": 1.5})], [("tool", "y")])
        block = "\n".join(lines[1:-1])
        self.assertIn("pathlib.Path('packages/a b/pyproject.toml')", block)
        self.assertIn("'on': True", block)
        self.assertEqual(follow.commands_of(block.split("\n")), [block])
        with self.assertRaises(render.PagesError):
            render.set_command("pyproject.toml", [(("tool", "x"), float("inf"))], [])



class ReviewCases(Case):
    "The cases of the adversarial review: the student's uv settings, a worktree, a change of spaces alone, a temporary folder in a repository."

    def setUp(self) -> None:
        "The project of SetByData's tutorial."
        super().setUp()
        needs_uv(self)
        self.start = commit(self.repo, {"pyproject.toml": START + DEV, "uv.lock": lock("0.17.0")}, "ruff")
        self.sha = commit(self.repo, {"pyproject.toml": START + DEV + RUFF}, "line length")

    def test_student_uv_settings(self) -> None:
        "A uv.toml of the student's that uv cannot meet stops neither git check nor the command that sets values."
        patch = hunks(START + DEV, START + DEV + RUFF)
        facts, stop = tutorial(LOOSE, self.start, self.sha, [{"kind": "patch", "mode": "shared", "path": "pyproject.toml"}],
                               [file_of("pyproject.toml", "patch", patch)])
        facts["toml_edits"] = render.toml_edits(self.repo, facts)
        page = "\n".join(render.stop_page(facts, stop, 1, "do", False))
        work = self.learner(facts, self.start)
        (work / "uv.toml").write_text('required-version = ">=99"\n\n[[index]]\nurl = "https://nowhere.invalid/simple"\ndefault = true\n')
        sh(work, "echo uv.toml >> .git/info/exclude")
        command = next(c for block in follow.blocks_of(page) for c in block.commands if c.startswith("uv run"))
        sh(work, command)
        done = sh(work, f"git check {self.sha}", check=False)
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))

    def test_worktree(self) -> None:
        "git check works in a second worktree of the student's clone, which has a git folder of its own."
        work = self.learner({"walk": {"loose": LOOSE}}, self.start)
        sh(work, f"git worktree add -q ../second {self.start}")
        second = work.parent / "second"
        (second / "pyproject.toml").write_text((START + DEV).replace("0.17.0", "0.17.1"))
        done = sh(second, f"git check {self.start}", check=False)
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))

    def test_spaces_alone(self) -> None:
        "A patch$ line that changes only a comment gets no command, and the page says why."
        sha = commit(self.repo, {"pyproject.toml": "# a comment\n" + START + DEV + RUFF}, "a comment")
        facts, stop = tutorial(LOOSE, self.sha, sha, [{"kind": "patch", "mode": "shared", "path": "pyproject.toml"}],
                               [file_of("pyproject.toml", "patch", "@@ -1 +1,2 @@\n+# a comment\n [project]\n")])
        facts["toml_edits"] = render.toml_edits(self.repo, facts)
        page = "\n".join(render.stop_page(facts, stop, 1, "do", False))
        self.assertNotIn("uv run", page)
        self.assertIn("changes no value", page)

    def test_temporary_folder_in_a_repository(self) -> None:
        "The patch is taken back right when the temporary folder is inside a git repository."
        left = START + DEV
        after = left + '\n[tool.uv]\ndefault-groups = ["dev"]\n'
        sha = commit(self.repo, {"pyproject.toml": after}, "more")
        parts = [{"kind": "command", "text": "uv add --dev ruff", "makes": True, "mode": "shared", "track": "", "writes": ["pyproject.toml"]},
                 {"kind": "patch", "mode": "shared", "path": "pyproject.toml"}]
        facts, _ = tutorial(LOOSE, self.start, sha, parts, [file_of("pyproject.toml", 0, hunks(left, after))])
        inside = self.repo / "tmp"
        inside.mkdir()
        saved = tempfile.tempdir
        tempfile.tempdir = str(inside)
        try:
            edits = render.toml_edits(self.repo, facts)
        finally:
            tempfile.tempdir = saved
        self.assertEqual(edits[f"{sha}:pyproject.toml"], ([(("tool", "uv"), {"default-groups": ["dev"]})], []))

    def test_remove_beside_an_array_of_tables(self) -> None:
        "Removing a key under a key that the student's file holds as an array of tables does nothing, and does not fail."
        work = self.folder / "aot"
        work.mkdir()
        (work / "pyproject.toml").write_text('[project]\nname = "demo"\n\n[[tool.x]]\na = 1\n')
        block = "\n".join(render.set_command("pyproject.toml", [], [("tool", "x", "y")])[1:-1])
        sh(work, block)
        self.assertIn("[[tool.x]]", (work / "pyproject.toml").read_text())


class OnlyUv(Case):
    "Dependencies and uv.lock change only through uv commands: just check names a patch$ line that changes them."

    def gaps(
        self,
        after: str,  # pyproject.toml after the move
        path: str = "pyproject.toml",  # The file that the patch$ line names
    ) -> list[str]:  # What dependency_gaps finds
        "Commit a move that changes pyproject.toml by patch$, and check it."
        start = commit(self.repo, {"pyproject.toml": START + DEV, "uv.lock": lock("0.17.0")}, "start")
        sha = commit(self.repo, {"pyproject.toml": after, "uv.lock": lock("0.18.0")}, "move")
        facts, _ = tutorial(LOOSE, start, sha, [{"kind": "patch", "mode": "shared", "path": path}],
                            [file_of("pyproject.toml", "patch", "@@ -1 +1 @@\n-a\n+b\n"), file_of("uv.lock", "patch", "@@ -1 +1 @@\n-a\n+b\n")])
        return render.dependency_gaps(self.repo, facts)

    def test_a_dependency(self) -> None:
        "A patch$ line that adds a package to dependencies, or changes the group dev, is a problem."
        for after in (START.replace("[]", '["six"]') + DEV, START + DEV.replace("ruff>=0.17.0", "ruff>=0.18.0")):
            found = self.gaps(after)
            self.assertEqual(len(found), 1, found)
            self.assertIn("change dependencies with uv add or uv remove on a do$ line", found[0])

    def test_uv_lock(self) -> None:
        "A patch$ line of uv.lock is always a problem."
        found = self.gaps(START + DEV, "uv.lock")
        self.assertEqual(len(found), 1, found)
        self.assertIn("uv.lock is written by uv; give the uv command on a do$ line", found[0])

    def test_other_tables(self) -> None:
        "A patch$ line that adds [tool.ruff] or changes the version is no problem."
        self.assertEqual(self.gaps(START.replace("0.1.0", "0.2.0") + DEV + RUFF), [])


if __name__ == "__main__":
    unittest.main()
