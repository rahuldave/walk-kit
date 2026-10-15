"""Tests of the writing review: the commit of each section of the notes, the reviewer's permissions, and style.py --all.

Run them with `python3 -m unittest discover -s tests`, from walk-kit. `just test` runs them first. `TimewalkTest` clones
timewalk-test's repo/ (TIMEWALK_TEST, default ~/Projects/timewalk-test) into a temporary folder, with its notes, and runs
timewalk-export from TIMEWALK there, so `just build` in timewalk-test cannot change the repository under a test.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import review
import style

TIMEWALK_TEST = Path(os.environ.get("TIMEWALK_TEST", Path.home() / "Projects/timewalk-test"))


def git(
    folder: Path,  # A repository
    *args: str,  # Arguments to git
) -> str:  # What git printed, without the trailing newline
    "Run git in a folder, as a fixed author."
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    return subprocess.run(["git", *args], cwd=folder, capture_output=True, text=True, check=True, env=env).stdout.strip()


def commit(
    repo: Path,  # A repository
    subject: str,  # The commit's subject
    tag: str = "",  # A tag to put on it, or ""
    annotated: bool = False,  # True for an annotated tag
) -> str:  # The new commit
    "Commit a change of one file, and tag it."
    (repo / "log.txt").write_text((repo / "log.txt").read_text() + subject + "\n" if (repo / "log.txt").exists() else subject + "\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", subject)
    if tag:
        git(repo, "tag", *(["-a", "-m", f"The note of {tag}"] if annotated else []), tag)
    return git(repo, "rev-parse", "HEAD")


NOTES = """# A small walk

The walk in a few words.

## step-00 Where it starts

Nothing yet.

## step-01 One commit

```markdown
## step-02 A heading in a fence is no section
```

## step-02 Three moves

The step in a few words.

### step-02.1 The first move

Text.

### A heading that names no move

More text of the first move.

### step-02.2 The second move

Text.

### step-02.3 The third move

Text.
"""

OWN = """The intro of a walk with notes of its own.

## Two tests

{{include step-02.1}}

Words between.

{{include step-02.2..step-02.3}}

## A stop with no include

Words.
"""


def stop(
    name: str,  # The stop's name
    start: str | None,  # The commit before it, or None for a first stop
    at: str,  # Its commit
    moves: list[tuple[str, str]] = (),  # Its moves: each name and commit
    own: str | None = None,  # The title of its ## heading, in a walk with notes of its own
) -> dict:  # A stop of the facts, with the fields that the review reads
    "Make a stop of the facts that timewalk-export --json writes."
    return {"name": name, "start": start, "commit": at, "own": {"title": own, "text": ""} if own else None,
            "moves": [{"name": move, "commit": commit} for move, commit in moves]}


class SmallWalk(unittest.TestCase):
    "A project of three steps, the last with three moves, and a parts-* walk beside them."

    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory()
        self.repo = Path(self.scratch.name) / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        self.c = {"step-00": commit(self.repo, "start", "step-00", annotated=True),
                  "step-01": commit(self.repo, "step-01: one commit", "step-01")}
        self.c["step-02.1"] = commit(self.repo, "step-02.1: first")
        self.c["step-02.2"] = commit(self.repo, "step-02.2: second")
        self.c["step-02.3"] = self.c["step-02"] = commit(self.repo, "step-02: third", "step-02", annotated=True)
        self.c["step-03"] = commit(self.repo, "step-03: one commit", "step-03")
        c = self.c
        self.facts = {"stops": [stop("step-00", None, c["step-00"]), stop("step-01", c["step-00"], c["step-01"]),
                                stop("step-02", c["step-01"], c["step-02"], [("step-02.1", c["step-02.1"]), ("step-02.2", c["step-02.2"]),
                                                                             ("step-02.3", c["step-02"])])]}
        self.named = review.walk_names(self.facts)

    def tearDown(self) -> None:
        self.scratch.cleanup()

    def test_walk_names_take_the_commits_of_the_facts(self) -> None:
        self.assertEqual(self.named["step-00"], ("", self.c["step-00"]))   # a first stop has no Before
        self.assertEqual(self.named["step-01"], (self.c["step-00"], self.c["step-01"]))
        self.assertNotIn("step-01.1", self.named)   # a step of one commit has no moves
        self.assertEqual(self.named["step-02.1"], (self.c["step-01"], self.c["step-02.1"]))   # a first move starts at its stop's start
        self.assertEqual(self.named["step-02.2"], (self.c["step-02.1"], self.c["step-02.2"]))
        self.assertEqual(self.named["step-02.3"], (self.c["step-02.2"], self.c["step-02"]))
        self.assertEqual(self.named["step-02"], (self.c["step-01"], self.c["step-02"]))

    def test_a_walk_that_picks_steps_has_its_own_before(self) -> None:
        # steps = ["step-01", "step-03"]: timewalk starts step-03 at step-01, and step-01 at nothing, though tags lie between
        picked = review.walk_names({"stops": [stop("step-01", None, self.c["step-01"]), stop("step-03", self.c["step-01"], self.c["step-03"])]})
        found = {s["heading"]: s for s in review.sections("## step-01 One\n\nText.\n\n## step-03 Three\n\nText.\n", picked)}
        self.assertEqual(found["## step-01 One"]["before"], "")
        self.assertEqual(found["## step-03 Three"]["before"], self.c["step-01"])
        self.assertIn("| none: the first step |", review.table(Path("n.md"), list(found.values()), self.repo).split("## step-01 One")[1])

    def test_sections_of_notes(self) -> None:
        found = {s["heading"]: s for s in review.sections(NOTES, self.named)}
        self.assertEqual(list(found), ["## step-00 Where it starts", "## step-01 One commit", "## step-02 Three moves",
                                       "### step-02.1 The first move", "### A heading that names no move",
                                       "### step-02.2 The second move", "### step-02.3 The third move"])
        self.assertEqual((found["## step-00 Where it starts"]["first"], found["## step-00 Where it starts"]["last"]), (5, 8))
        self.assertEqual((found["## step-01 One commit"]["first"], found["## step-01 One commit"]["last"]), (9, 14))
        self.assertEqual(found["### step-02.1 The first move"]["at"], self.c["step-02.1"])
        self.assertEqual(found["### A heading that names no move"]["at"], self.c["step-02.1"])   # part of the move before it
        self.assertEqual(found["### step-02.2 The second move"]["before"], self.c["step-02.1"])

    def test_sections_of_a_walk_with_notes_of_its_own(self) -> None:
        c = self.c
        own = review.walk_names({"stops": [stop("step-02.1 to step-02.3", c["step-01"], c["step-02"],
                                                [("step-02.1", c["step-02.1"]), ("step-02.2", c["step-02.2"]), ("step-02.3", c["step-02"])],
                                                own="Two tests")]})
        found = review.sections(OWN, own)
        self.assertEqual([s["heading"] for s in found], ["## Two tests"])   # a stop that timewalk does not make has no commit
        self.assertEqual((found[0]["before"], found[0]["at"]), (c["step-01"], c["step-02"]))
        self.assertNotIn("## Two tests", review.walk_names({"stops": [stop("x", None, c["step-02"], own="Two tests")]}, own=False))

    def test_table_names_the_repository_and_each_commit(self) -> None:
        said = review.table(Path("notes.md"), review.sections(NOTES, self.named), self.repo)
        self.assertIn(f"git -C {self.repo} show COMMIT:PATH", said)
        self.assertIn(f"| 19-22 | ### step-02.1 The first move | {self.c['step-01'][:12]} | {self.c['step-02.1'][:12]} |", said)
        self.assertIn(f"| 5-8 | ## step-00 Where it starts | none: the first step | {self.c['step-00'][:12]} |", said)
        self.assertEqual(review.table(Path("x.md"), [], self.repo), "")

    def test_a_diff_says_the_section_of_each_hunk(self) -> None:
        notes = Path(self.scratch.name) / "class" / "notes.md"
        notes.parent.mkdir()
        git(notes.parent, "init", "-q", "-b", "main")
        notes.write_text(NOTES)
        git(notes.parent, "add", "-A")
        git(notes.parent, "commit", "-q", "-m", "notes")
        notes.write_text(NOTES.replace("More text of the first move.", "More text, changed.").replace("Nothing yet.", "Nothing at all."))
        text = review.text_of(notes, False, self.named, self.repo)
        self.assertIn("=== THE COMMIT OF EACH SECTION OF", text)
        self.assertIn("=== this hunk is in the section ## step-00 Where it starts ===", text)
        self.assertIn("=== this hunk is in the section ### A heading that names no move ===", text)
        self.assertIn("+More text, changed.", text)
        whole = review.text_of(notes, True, self.named, self.repo)
        self.assertIn("(the whole file)", whole)
        self.assertNotIn("this hunk", whole)
        self.assertNotIn("THE COMMIT", review.text_of(notes, True))   # without a project, no table

    def test_walk_files_give_each_file_the_names_of_its_walks(self) -> None:
        folder = Path(self.scratch.name) / "toc"
        folder.mkdir()
        c = self.c
        (folder / "toc.toml").write_text(
            '[[walk]]\nid = "picked"\nnotes = "picked.md"\nsteps = ["step-01", "step-03"]\n\n'
            '[[walk]]\nid = "small"\nnotes = "all.md"\nintro = "small.md"\nselect = ["step-03"]\n\n'
            '[[walk]]\nid = "all"\nnotes = "all.md"\n\n'
            '[[walk]]\nid = "own"\nnotes = "own.md"\nshared = "all.md"\n')
        facts = {"picked": {"stops": [stop("step-01", None, c["step-01"]), stop("step-03", c["step-01"], c["step-03"])]},
                 "small": {"stops": [stop("step-03", "0" * 40, c["step-03"])]},   # a Before of its own, which loses to the walk "all"
                 "all": self.facts | {"stops": [*self.facts["stops"], stop("step-03", c["step-02"], c["step-03"])]},
                 "own": {"stops": [stop("step-02.1", c["step-01"], c["step-02.1"], [("step-02.1", c["step-02.1"])], own="Two tests")]}}
        kept = review.export
        review.export = lambda repo, folder, walk, scratch: facts[walk["id"]]
        try:
            files = review.walk_files(folder, self.repo)
        finally:
            review.export = kept
        named = {path.name: names for path, names in files.items()}
        self.assertEqual(sorted(named), ["all.md", "own.md", "picked.md", "small.md"])   # a file of no walk is not there
        self.assertEqual(named["picked.md"]["step-03"], (c["step-01"], c["step-03"]))
        self.assertEqual(named["all.md"]["step-03"], (c["step-02"], c["step-03"]))   # the walk that keeps every step comes first
        self.assertEqual(named["small.md"]["step-03"], ("0" * 40, c["step-03"]))   # an intro takes its own walk
        self.assertEqual(named["own.md"], {"## Two tests": (c["step-01"], c["step-02.1"]), "step-02.1": (c["step-01"], c["step-02.1"])})
        self.assertNotIn("## Two tests", named["all.md"])   # the shared notes take the moves, and not the own titles
        self.assertEqual(review.walk_files(Path(self.scratch.name), self.repo), {})   # no toc.toml and no notes.md: no walk


class Permissions(unittest.TestCase):
    "The reviewer may read its folders, and run only git show, ls-tree and log in the project."

    def test_without_a_project_no_command(self) -> None:
        said = review.permissions(None)
        self.assertEqual(said[said.index("--tools") + 1], "Read,Grep,Glob")
        self.assertIn("--restricted", said)
        self.assertEqual(said[said.index("--permission-mode") + 1], "dontAsk")
        self.assertNotIn("--disallowedTools", said)

    def test_with_a_project_git_reads_only(self) -> None:
        said = review.permissions(Path("/p/repo"))
        self.assertEqual(said[said.index("--tools") + 1], "Read,Grep,Glob,Bash")
        for verb in ("show", "ls-tree", "log"):
            self.assertIn(f"Bash(git -C /p/repo {verb}:*)", said)
        self.assertNotIn("Bash", [rule for rule in said if rule == "Bash"])   # never the whole of Bash
        self.assertIn("Bash(*--output*)", said[said.index("--disallowedTools"):])


class PlainPath(unittest.TestCase):
    "A project whose path has a space is read through a link, so that the model's git commands match the allow rules."

    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory()
        self.repo = Path(self.scratch.name) / "my class" / "repo"
        self.repo.mkdir(parents=True)
        git(self.repo, "init", "-q", "-b", "main")
        self.first = commit(self.repo, "start", "step-00")
        self.kept, review.LINKS = review.LINKS, Path(self.scratch.name) / "links"

    def tearDown(self) -> None:
        review.LINKS = self.kept
        self.scratch.cleanup()

    def test_a_path_with_a_space_gets_a_link(self) -> None:
        link = review.plain_path(self.repo)
        self.assertNotIn(" ", str(link))
        self.assertEqual(link.resolve(), self.repo.resolve())
        self.assertEqual(review.plain_path(self.repo), link)   # the same link each time, so the cache of reviews holds
        self.assertEqual(git(link, "rev-parse", "HEAD"), self.first)
        said = review.permissions(link)
        rules = [rule for rule in said if rule.startswith("Bash(git -C")]
        self.assertEqual(len(rules), 3)
        self.assertTrue(all(" " not in rule.removeprefix("Bash(git -C ").split(" ", 1)[0] for rule in rules), rules)
        table = review.table(Path("n.md"), [{"heading": "## step-00", "first": 1, "last": 2, "before": "", "at": self.first}], link)
        self.assertIn(f"git -C {link} show COMMIT:PATH", table)
        self.assertNotIn(str(self.repo), table)

    def test_a_plain_path_is_kept(self) -> None:
        plain = Path(self.scratch.name) / "plain"
        self.assertEqual(review.plain_path(plain), plain)
        self.assertFalse(review.LINKS.exists())

    def test_a_link_that_points_elsewhere_is_put_right(self) -> None:
        link = review.plain_path(self.repo)
        link.unlink()
        link.symlink_to(self.scratch.name)
        self.assertEqual(review.plain_path(self.repo).resolve(), self.repo.resolve())


class StyleAll(unittest.TestCase):
    "style.py passes --all on to the review, which then reviews each file whole."

    def run_style(
        self,
        *args: str,  # Arguments to style.py after --class
    ) -> tuple:  # The arguments that style.py gave review.run
        "Run style.py on a class with a README that passes the form, with review.run replaced."
        with tempfile.TemporaryDirectory() as scratch:
            folder = Path(scratch)
            (folder / "README.md").write_text("# Tally\n\nTally counts the words of a text.\n")
            (folder / "notes.md").write_text("# Notes\n\nThe notes of the class.\n")
            seen, kept, argv = [], review.run, sys.argv
            review.run = lambda *given: seen.append(given) or (0, [])
            sys.argv = ["style.py", "--class", str(folder), *args]
            try:
                code = style.main()
            finally:
                review.run, sys.argv = kept, argv
        self.assertEqual(code, 0)
        return seen[0]

    def test_all_reviews_whole_files(self) -> None:
        self.assertTrue(self.run_style("--all")[1])

    def test_without_all_only_the_change(self) -> None:
        self.assertFalse(self.run_style()[1])

    def test_repo_goes_to_the_review(self) -> None:
        self.assertEqual(self.run_style("--repo", "/p/repo")[3], Path("/p/repo"))


def copy_of_timewalk_test(
    source: Path,  # A timewalk-test folder, with repo/, toc.toml, notes.md and walks/
    scratch: Path,  # A temporary folder
) -> Path:  # A copy of the class in the temporary folder: a clone of repo/ with every tag, and the notes
    "Copy timewalk-test into a temporary folder, so that a test never reads the repository that `just build` there rewrites."
    folder = scratch / "class"
    folder.mkdir()
    git(scratch, "clone", "-q", "--no-local", str(source / "repo"), str(folder / "repo"))
    for name in ("toc.toml", "notes.md"):
        shutil.copy(source / name, folder / name)
    for name in ("walks", "slides"):
        if (source / name).is_dir():
            shutil.copytree(source / name, folder / name, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    return folder


def missing() -> str:  # What TimewalkTest lacks on this machine, or ""
    "Say why TimewalkTest cannot run here."
    if not (TIMEWALK_TEST / "repo" / ".git").exists():
        return f"{TIMEWALK_TEST}/repo is missing; run just build in timewalk-test, or set TIMEWALK_TEST"
    return "" if shutil.which("uvx") else "uvx is not on this machine, and timewalk-export runs through it"


class CopyOfTimewalkTest(unittest.TestCase):
    "The copy keeps its commits when the class it came from is built again."

    def test_a_rebuild_of_the_source_does_not_reach_the_copy(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            source = Path(scratch) / "source"
            (source / "repo").mkdir(parents=True)
            git(source / "repo", "init", "-q", "-b", "main")
            first = commit(source / "repo", "one", "step-01", annotated=True)
            (source / "toc.toml").write_text("")
            (source / "notes.md").write_text("## step-01 One\n")
            copy = copy_of_timewalk_test(source, Path(scratch))
            git(source / "repo", "commit", "-q", "--amend", "-m", "one, built again")   # as just build rewrites the history
            git(source / "repo", "tag", "-f", "-a", "-m", "again", "step-01")
            self.assertNotEqual(git(source / "repo", "rev-parse", "step-01^{commit}"), first)
            self.assertEqual(git(copy / "repo", "rev-parse", "step-01^{commit}"), first)


@unittest.skipIf(missing(), missing())
class TimewalkTest(unittest.TestCase):
    "The tables of real walks, from timewalk-export, in a copy of timewalk-test."

    @classmethod
    def setUpClass(cls) -> None:
        cls.scratch = tempfile.TemporaryDirectory()
        cls.folder = copy_of_timewalk_test(TIMEWALK_TEST, Path(cls.scratch.name))
        cls.repo = cls.folder / "repo"
        cls.files = review.walk_files(cls.folder, cls.repo)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.scratch.cleanup()

    def found(
        self,
        name: str,  # A notes file, from the class folder
    ) -> list[dict]:  # Its sections, from sections
        "Find the sections of a notes file of the copy, with the names of its walks."
        path = self.folder / name
        return review.sections(path.read_text(), self.files[path.resolve()])

    def test_each_move_heading_has_its_commit(self) -> None:
        moves = [s for s in self.found("walks/tutorial/notes.md") if s["heading"].startswith("### step-")]
        self.assertGreater(len(moves), 5)
        for section in moves:
            name = section["heading"].split()[1]
            subject = git(self.repo, "log", "-1", "--format=%s", section["at"])
            self.assertTrue(subject.startswith((name, name.split(".")[0])), (name, subject))
            self.assertEqual(git(self.repo, "rev-parse", f"{section['at']}^"), section["before"])

    def test_steps_are_their_tags(self) -> None:
        for section in self.found("notes.md"):
            name = section["heading"].split()[1]
            self.assertEqual(section["at"], git(self.repo, "rev-parse", f"{name}^{{commit}}"))

    def test_a_walk_that_picks_steps_starts_each_at_the_step_before_it(self) -> None:
        # walks/tests: steps = ["step-01", "step-02", "step-05"]. step-05 starts at step-02, and step-01 at nothing
        found = {s["heading"].split()[1]: s for s in self.found("walks/tests/notes.md")}
        self.assertEqual(found["step-01"]["before"], "")
        self.assertEqual(found["step-05"]["before"], git(self.repo, "rev-parse", "step-02^{commit}"))
        self.assertEqual(found["step-05"]["at"], git(self.repo, "rev-parse", "step-05^{commit}"))

    def test_a_stop_of_notes_of_its_own_has_the_commits_of_its_includes(self) -> None:
        found = {s["heading"]: s for s in self.found("walks/testing/notes.md")}
        stop = found["## Three tests of counting"]   # {{include step-02.1}} and {{include step-02.2..step-02.3}}
        self.assertEqual(stop["before"], git(self.repo, "rev-parse", "step-01^{commit}"))
        self.assertEqual(stop["at"], git(self.repo, "rev-parse", "step-02^{commit}"))


if __name__ == "__main__":
    unittest.main()
