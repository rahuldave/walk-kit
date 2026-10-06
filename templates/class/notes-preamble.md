# Notes for the @project@ class

Each step has one section, which starts with `## step-name Title`. timewalk shows the section of the current step in the
notes column of its page, every line of it.

- **`time: 0:23`** is when the step should start, in minutes and seconds into the class. The clock band
  uses it, with `--clock`. The notes column and the PDF leave it out.
- **A command** is a line that starts with `$ `. A click on it types the command into the terminal of the
  step. With **run on click** on, a click also runs it. `runs$ ` sends it to the Runs tab, for a command
  that takes a while, and `main$ ` to the Main tab, in the project itself.
- **A cue** is a line that starts with `> `, for example `> Say: ...` or `> Note: ...`. The notes column
  shows it shaded. `> Say:` and `> Note:` lines are private. `just walk-update` leaves them out, and the `time:`
  lines too. The notes are not in the PDF: they are for the step browser.
- **Edit** at the top of the notes column changes the section of the step. **Save** writes it into this
  file.
- **A move throws away edits.** `just present` starts timewalk with `--discard-edits`. So a script puts a
  file back only when a later command of the same step needs it clean.

