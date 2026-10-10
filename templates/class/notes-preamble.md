# Notes for the @project@ class

Each step has one section, which starts with `## step-name Title`. timewalk shows the section of the current step in the
notes column of its page, every line of it.

- **`time: 0:23`** is when the step should start, in minutes and seconds into the class. The clock band
  uses it, with `--clock`. The notes column and the PDF leave it out.
- **A command** is a line that starts with `$ `. A click on it types the command into the terminal of the
  step. With **run on click** on, a click also runs it. `runs$ ` sends it to the Runs tab, for a command
  that takes a while, and `main$ ` to the Main tab, in the project itself.
- **A cue** is a line that starts with `> `, for example `> Say: ...` or `> Note: ...`. The notes column
  shows it shaded. `> Say:` and `> Note:` lines are private, with their whole blockquote, up to a blank line. Put a
  blank line between a private cue and a public one, such as `> Try:`.
  `just walk-update` leaves them out, and the `time:` lines too. The notes are not in the PDF: they are for the step browser.
- **Edit** at the top of the notes column changes the section of the step. **Save** writes it into this
  file.
- **`$ just setup` starts every step.** It is the project's own recipe, at the step. It makes the environment and
  what the step needs, and never touches git. Every command runs through `uv run` or a `just` recipe.
- **A move of a tutorial** has a section of its own, `### step-NN.k Title`, under its step. `WALKS.md` in the walk
  skill says what the section holds.
- **Files changed are a list.** Never name them inside a sentence. Write "These are the files changed:", then one
  item for each file: its path in code, then what happened to it. Say what matters after the list.
- **A move keeps edits.** timewalk steps in a replay copy, a clone of the project beside it. Before a move, it keeps
  the edits and commits made there on a branch `timewalk/saved/<step>`, and does not ask. After a command that
  changes files, `git restore .` keeps that notice away.

