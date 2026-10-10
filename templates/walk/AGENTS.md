# The walk through @project@

This repository is a walk for timewalk. It replays the steps of the project @upstream@/@project@. A student
forks it, runs `just present`, and opens the address that timewalk prints.

- `walk.md` holds the notes of every step. With several walks, `toc.toml` lists them, and says where the notes of
  each one are. The student edits the notes on the page, or in an editor.
- `repo/` is a clone of the project, and `worktree/` is timewalk's replay copy, a clone of `repo/` on the branch
  `timewalk/replay`. Git ignores both. timewalk never writes to `repo/`.
- Work in `repo/` on `main`, and push to the student's own fork of the project. A move between steps keeps the
  edits and commits in `worktree/` on a branch `timewalk/saved/<step>` there, and does not ask. A `worktree/`
  from an older timewalk is a git worktree, where a move with edits asks and stashes them. Keep what the student
  needs from it, delete it, and run `git -C repo worktree prune`. The next `just present` makes a clone.
- In a tutorial, a step has moves, the small commits between two tags. The moves go in order. To go back, use
  **Restart step**, and then `just setup`.
- `just pdf` makes `build/walk.pdf`, the slides, one page each. The notes are not in it. Git ignores it.
- Do not change `justfile` or `.gitignore` for one student's needs. The teacher's class material makes them.
