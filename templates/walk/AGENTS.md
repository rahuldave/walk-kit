# The walk through @project@

This repository is a kit for timewalk. It replays the steps of the project @upstream@/@project@. A student
forks it, runs `just present`, and opens the address that timewalk prints.

- `walk.md` holds the notes of every step. The student edits them on the page, or in an editor.
- `repo/` is a clone of the project, and `worktree/` is timewalk's replay copy. Git ignores both.
- Work in `repo/` on `main`, and push to the student's own fork of the project. A move between steps
  throws away edits in `worktree/`.
- `just pdf` makes `walk.pdf`. Git ignores it.
- Do not change `justfile` or `.gitignore` for one student's needs. The teacher's class material makes them.
