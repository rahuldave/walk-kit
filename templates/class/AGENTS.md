# The class material for @project@

This repository is private. It holds the material for a class that walks through the steps of
@project@ with timewalk. The project is `../@project@`, beside this folder, and the public walk
repository for students is `../@project@-walk`. `just setup` clones them there if they are missing.

## What is here

| Path | Holds |
|---|---|
| `notes.md` | The script of every step, one `## step-name Title` section for each tag of the project |
| `slides/` | The slides, and `slides.toml`, the manifest that says which slides show at which step. Rename `slides.example.toml` to `slides.toml` once it has a line for every step. Keep no notes in this folder: `just walk-update` copies it whole |
| `toc.toml` | Only in a class with several walks: the list of walks, the first one the default |
| `walks/ID/` | Only in a class with several walks: the `notes.md` and `slides/` of each walk after the first |
| `justfile` | The recipes. `just` lists them |
| `build/` | What the recipes make. Git ignores it |

## The rules of the notes

Read `WALKS.md` in the walk skill before you write the notes of a walk, and before you add a walk. It says what a
narrative and a tutorial need, and the rules of `just setup`.

- **Private lines.** A line that starts with `> Say:` or `> Note:`, and a line `time: m:ss`, stay here, also
  when they are indented. So does the whole blockquote of a cue, up to a blank line: end a cue with a blank line. A
  blockquote with a private cue and a public cue, such as `> Try:`, stops `just walk-update`.
  `just walk-update` leaves them out. Every other line goes to students. No PDF has notes: the notes are for the step browser.
- **Commands.** A line `$ command` is a command for the terminal at the step. `runs$` and `main$` send it
  to other tabs.
- **Every command runs through `uv run` or a `just` recipe**, never a bare `python`. Each step's notes start with
  `$ just setup`.
- **Rehearse every command** at its step, or at its move in a tutorial, in the replay copy before it goes into the notes.
- **No colon before a command.** Write "The last command undoes them", and not "Undo them with:".

## The recipes

| Recipe | Does |
|---|---|
| `just setup` | Clones the project and `@project@-walk` beside this folder if they are missing, and checks for the skill. Run it first in a fresh clone |
| `just present` | Opens the walk on the project, with these notes and slides and the clock. `just present ID` opens another walk of `toc.toml` |
| `just check` | Checks the notes and the slides of every walk against the steps, and a tutorial's moves |
| `just draft ID` | Drafts the notes of the moves of a tutorial from its commits. `just draft ID --write` adds them to its notes |
| `just pdf` | Makes `build/@project@.pdf`, the slides, one page each, for you and for the students. The notes are not in it. `just pdf ID` makes the PDF of another walk |
| `just check-pdf` | Checks that no slide is cut off in that PDF |
| `just walk-init` | Makes `@project@-walk`, once. Asks before it creates the public repository |
| `just walk-update` | Refreshes `@project@-walk` from the notes and the slides of every walk. Shows the diff, and commits on a yes. Never pushes |

The scripts behind the last three are the walk skill's, in `~/.agents/skills/walk`. Do not copy them here.
