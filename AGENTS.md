# Working on walk-kit

walk-kit is a skill (`SKILL.md`) and the scripts behind it. Read `SKILL.md` and `README.md` first.

- **No project names in the code.** Every script takes the project, the owner and the paths as arguments.
- **One place for each fact.** Where timewalk comes from is in `scripts/common.py`, unpinned. The private lines are
  in `scripts/private.py`. A template takes a value through `@key@`, and never repeats one.
- **Standard library only.** The scripts run with `python3`, with nothing to install.
- **Ask before** a commit, a push, or a repository on GitHub. The scripts ask too.
- **Test a change** with a throwaway project. Run `class_init.py` and `walk_init.py` with `--no-github`
  in a temporary folder, and then delete the folder.
- **Write documentation** in short sentences, with one term for one thing, and no dashes.
