# Working on walk-kit

walk-kit is a skill (`SKILL.md`) and the scripts behind it. Read `SKILL.md` and `README.md` first.

- **No project names in the code.** Every script takes the project, the owner and the paths as arguments.
- **One place for each fact.** `scripts/common.py` says where timewalk comes from, timewalk's `main`, unpinned.
  The private lines are in `scripts/private.py`. A template takes a value through `@key@`, and never repeats one.
- **Never delete timewalk's branch `walks`.** The justfiles of older student forks name `@walks`. Keep the branch, and
  move it to the commit of `main` at each release of timewalk.
- **walk-update writes only into the walk repository.** Every write, delete and copy goes through `target()` in
  `walk_update.py`, and every file is written by `write()`, as a new file. `within()` compares folders by what they are
  on the disk, and not by their text. When in doubt about a path or a private line, refuse with a message, and do not guess.
- **Standard library only.** The scripts run with `python3`, with nothing to install.
- **Ask before** a commit, a push, or a repository on GitHub. The scripts ask too.
- **Test a change** with a throwaway project. Run `class_init.py` and `walk_init.py` with `--no-github`
  in a temporary folder, and then delete the folder.
  `just test` follows the Build it yourself pages of timewalk-test, and every `git check` must pass. It also checks
  every page to read with `scripts/read_check.py`. A page to read has nothing to run, every move with its diffs, and
  links that resolve, and its website builds. `just test-github` does both for the pages of tally-walk on GitHub, with every link asked of GitHub.
- **Write by the guide.** Every Markdown file and template follows `style/GUIDE.md`, the nossaifd writing guide.
  Check them with `python3 style/check.py README.md SKILL.md WALKS.md AGENTS.md style/README.md templates/*/*.md`,
  and fix every hard problem.
