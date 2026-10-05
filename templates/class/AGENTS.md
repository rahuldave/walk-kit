# The class material for @project@

This repository is private. It holds the material for a class that walks through the steps of
@project@ with timewalk. The project is `../@project@`, beside this folder, and the public walk
repository for students is `../@project@-walk`. `just setup` clones them there if they are missing.

## What is here

| Path | Holds |
|---|---|
| `notes.md` | The script of every step, one `## step-name Title` section for each tag of the project |
| `slides/` | The slides, and `slides.toml`, the manifest that says which slides show at which step |
| `justfile` | The recipes. `just` lists them |
| `build/` | What the recipes make. Git ignores it |

## The rules of the notes

- **Private lines.** A line that starts with `> Say:` or `> Note:`, and a line `time: m:ss`, stay here.
  `just walk-update` and `just student-pdf` leave them out. Every other line goes to students.
- **Commands.** A line `$ command` is a command for the terminal at the step. `runs$` and `main$` send it
  to other tabs.
- **Rehearse every command** at its step in the replay copy before it goes into the notes.
- **No colon before a command.** Write "The last command undoes them", and not "Undo them with:".

## The recipes

| Recipe | Does |
|---|---|
| `just setup` | Clones the project and `@project@-walk` beside this folder if they are missing, and checks for the skill. Run it first in a fresh clone |
| `just present` | Opens the walk on the project, with these notes and slides and the clock |
| `just handout` | Makes `build/@project@-handout.pdf`, with the private cues, for the teacher |
| `just student-pdf` | Makes `build/@project@-student.pdf`, without the private cues, to give to students |
| `just walk-init` | Makes `@project@-walk`, once. Asks before it creates the public repository |
| `just walk-update` | Refreshes `@project@-walk` from `notes.md` and `slides/`. Shows the diff, and commits on a yes. Never pushes |

The scripts behind the last three are the walk skill's, in `~/.agents/skills/walk`. Do not copy them here.
