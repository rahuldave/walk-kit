# The walk through @project@, step by step

This file holds the notes of every step of a walk. timewalk shows the notes of the current step in the column on the
right of the page.

- **A command** is a line that starts with `$ `. A click on it types the command into the terminal of the
  step, and you press Enter to run it. With **run on click** on, a click also runs it.
- **Other tabs:** a line that starts with `runs$ ` goes to the **Runs** tab, for a command that takes a
  while. A line that starts with `main$ ` goes to the **Main** tab, in `repo/`.
- **A cue** is a line that starts with `> `. The notes column shows it shaded.
- **Edit** at the top of the column changes the notes of the step, and **Save** writes them into
  this file. Commit it to your fork to keep your notes.
- **`$ just setup` starts every step.** It is the project's own recipe, at the step. It makes the environment
  of the step, and what the step needs.
- **A move keeps your work.** Before a move, timewalk keeps your edits and commits in `worktree/` on a branch
  `timewalk/saved/<step>`, and the page says how to get them back.

