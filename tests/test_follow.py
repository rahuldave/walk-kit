"""follow.py: a student who follows a page, on a small project of two moves, with pages written by hand."""

import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "scripts"))

import follow

ALIAS = """git config alias.check '!f() { git add -A && git diff --cached --stat "$1"; }; f'"""


def git(
    cwd: Path,  # The repository
    *args: str,  # Arguments to git
) -> str:  # What git printed
    "Run git with a fixed author."
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
           "GIT_CONFIG_GLOBAL": "/dev/null", "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin", "HOME": str(cwd)}
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True, env=env).stdout.strip()


def fence(
    *lines: str,  # The commands
) -> str:  # A ```bash block
    "Write a block of shell."
    return "```bash\n" + "\n".join(lines) + "\n```\n"


def catch_up(
    sha: str,  # The commit whose files to put in place
) -> str:  # The catch-up block, as render.py writes it
    "Write the command for a student who is stuck."
    return fence(f"git restore --source {sha} --staged -- :/ && git restore --source {sha} --staged --worktree -- :/")


class Follow(unittest.TestCase):
    """A project with three commits: a file, a line added, a second file."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "proj"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "a.txt").write_text("one\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "start")
        self.start = git(self.repo, "rev-parse", "HEAD")
        (self.repo / "a.txt").write_text("one\ntwo\n")
        git(self.repo, "commit", "-qam", "two")
        self.two = git(self.repo, "rev-parse", "HEAD")
        (self.repo / "b.txt").write_text("bee\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "bee")
        self.bee = git(self.repo, "rev-parse", "HEAD")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def setup_block(self) -> str:
        "Get the project, at the first commit."
        return "## Get the project\n\n" + fence("git clone https://github.com/o/proj", "cd proj", f"git switch -qc mine {self.start}", ALIAS)

    def patch(self, sha: str) -> str:
        "The patch of one commit, from GitHub."
        return fence(f"curl -fsSL https://github.com/o/proj/commit/{sha}.diff | git apply")

    def follow(
        self,
        page: str,  # The page
        *extra: str,  # More arguments
    ) -> tuple[int, str]:  # The exit code, and what follow.py printed
        "Follow a page in a fresh scratch folder."
        path = self.root / "build.md"
        path.write_text(page)
        work = Path(tempfile.mkdtemp(dir=self.root))
        done = subprocess.run([sys.executable, str(KIT / "scripts" / "follow.py"), str(path), "--repo", str(self.repo), "--work",
                               str(work / "w"), *extra], capture_output=True, text=True, timeout=120, check=False)
        return done.returncode, done.stdout + done.stderr

    def test_a_right_page_passes(self) -> None:
        page = (self.setup_block() + "## Two\n\n" + self.patch(self.two) + fence(f"git check {self.two}") + catch_up(self.two)
                + "## Bee\n\n" + self.patch(self.bee) + fence(f"git check {self.bee}") + catch_up(self.bee))
        code, said = self.follow(page)
        self.assertEqual(code, 0, said)
        self.assertIn("follow: 2 checks, 0 failed", said)

    def test_a_wrong_move_fails_and_the_catch_up_lets_the_next_pass(self) -> None:
        page = (self.setup_block() + "## Two\n\n" + fence("echo nothing") + fence(f"git check {self.two}") + catch_up(self.two)
                + "## Bee\n\n" + self.patch(self.bee) + fence(f"git check {self.bee}") + catch_up(self.bee))
        code, said = self.follow(page)
        self.assertEqual(code, 1, said)
        self.assertIn(f"FAIL git check {self.two}", said)
        self.assertIn(f"ok   git check {self.bee}", said)
        self.assertIn("follow: 2 checks, 1 failed", said)

    def test_the_catch_up_is_skipped_after_a_check_that_passed(self) -> None:
        # a catch-up to the wrong commit: if it ran, the next check would fail
        page = (self.setup_block() + "## Two\n\n" + self.patch(self.two) + fence(f"git check {self.two}") + catch_up(self.start)
                + "## Bee\n\n" + self.patch(self.bee) + fence(f"git check {self.bee}"))
        code, said = self.follow(page)
        self.assertEqual(code, 0, said)

    def test_a_page_without_a_check_fails(self) -> None:
        code, said = self.follow(self.setup_block() + "## Two\n\n" + self.patch(self.two))
        self.assertEqual(code, 1, said)
        self.assertIn("no git check on the page", said)

    def test_a_check_that_does_not_run_fails(self) -> None:
        # the check sits in a here-document, so the page counts it but the student never runs it
        page = (self.setup_block() + "## Two\n\n" + self.patch(self.two) + fence(f"git check {self.two}")
                + fence("cat > notes.txt <<'EOF'", f"git check {self.two}", "EOF"))
        code, said = self.follow(page)
        self.assertEqual(code, 1, said)
        self.assertIn("2 git check lines, and 1 ran", said)

    def test_a_command_that_fails_is_not_a_failure(self) -> None:
        page = self.setup_block() + "## Two\n\n" + fence("false") + self.patch(self.two) + fence(f"git check {self.two}")
        code, said = self.follow(page)
        self.assertEqual(code, 0, said)

    def test_a_server_left_running_does_not_hold_the_run(self) -> None:
        page = self.setup_block() + "## Two\n\n" + fence("sleep 300 &") + self.patch(self.two) + fence(f"git check {self.two}")
        began = time.monotonic()
        code, said = self.follow(page)
        self.assertEqual(code, 0, said)
        self.assertLess(time.monotonic() - began, 60)

    def test_github_runs_the_curl_as_written(self) -> None:
        line = f"curl -fsSL https://github.com/o/proj/commit/{self.two}.diff | git apply"
        self.assertEqual(follow.Student(self.repo, self.root, github=True).translate(line), line)
        self.assertNotIn("curl", follow.Student(self.repo, self.root).translate(line))

    def test_github_clones_from_the_address(self) -> None:
        # o/proj does not exist: the clone must fail, not take --repo
        code, said = self.follow(self.setup_block() + "## Two\n\n" + fence(f"git check {self.two}"), "--github")
        self.assertNotEqual(code, 0, said)
        self.assertIn("cannot clone https://github.com/o/proj", said)


class Commands(unittest.TestCase):
    """How a block splits into the commands that a student types."""

    def test_a_here_document_stays_with_its_command(self) -> None:
        self.assertEqual(follow.commands_of(["cat > f <<'EOF'", "a << b", "EOF", "ls"]), ["cat > f <<'EOF'\na << b\nEOF", "ls"])

    def test_a_shift_and_a_here_string_are_not_here_documents(self) -> None:
        self.assertEqual(follow.heredocs("echo $((1 << 2)); cat <<< word"), [])
        self.assertEqual(follow.heredocs("echo '<<EOF'"), [])

    def test_a_continued_line_is_one_command(self) -> None:
        self.assertEqual(follow.commands_of(["echo a \\", "  b", "# note", "", "ls"]), ["echo a \\\n  b", "ls"])

    def test_an_indented_fence_in_a_list(self) -> None:
        page = "1. Run it:\n\n   ```sh\n   git check abc\n   ```\n"
        self.assertEqual(follow.checks_in(page), 1)
        self.assertEqual(follow.blocks_of(page)[0].commands, ["git check abc"])


if __name__ == "__main__":
    unittest.main()
