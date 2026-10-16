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
| `site.toml` | Only for a website with a smalldocs theme: `theme = "owner/repo@ref"`, and a table `[smalldocs]` of settings. WALKS.md of walk-kit, "A theme for the website", says how |
| `walks/ID/` | Only in a class with several walks: the `notes.md` and `slides/` of each walk after the first |
| `justfile` | The recipes. `just` lists them |
| `build/` | What the recipes make. Git ignores it |
| `reports/` | The reviews of a model are in `reports/writing/` and `reports/follow/`, which git ignores. Other reports in `reports/` are tracked |

## The rules of the notes

Read `WALKS.md` in the walk skill before you write the notes of a walk, and before you add a walk. It says what a
narrative and a tutorial need, and the rules of `just setup`.

- **Private lines.** A line that starts with `> Say:` or `> Note:`, and a line `time: m:ss`, stay here, also
  when they are indented. So does the whole blockquote of a cue, up to a blank line. End a cue with a blank line. A
  blockquote with a private cue and a public cue, such as `> Try:`, stops `just walk-update`.
  `just walk-update` leaves them out. Every other line goes to students. No PDF has notes. The notes are for the
  step browser.
- **Commands.** A line `$ command` is a command for the terminal at the step. `runs$` and `main$` send it
  to other tabs.
- **Every command runs through `uv run` or a `just` recipe**, never a bare `python`. Each step's notes start with
  `$ just setup`.
- **Rehearse every command** in the replay copy, at its step or at its move in a tutorial. Then put it into the notes.
- **Write for a reader who has never heard of timewalk.** Students also read the notes as pages, without timewalk.
  Keep the words "step", "commit" and "Start" out of the text. Explain a move once, in the intro of each tutorial. A move
  is one small change, made by one patch or one command, which the page checks. Then the text can use the word "move". Give the problem and the change first. Then
  give the change piece by piece, and the check. Last, give `files:` with an item for every file. Give each file of a
  move a `do$` line or a `patch$` line, in the text for both modes. `WALKS.md` in the walk skill gives the rules.
- **No colon before a command.** Write "The last command undoes them", and not "Undo them with:".
- **Write by the guide.** Everything here follows the nossaifd writing guide, `style/GUIDE.md` in the walk skill. Read
  it before you write. `just style` checks the prose. Fix every hard problem before a commit.

## The recipes

| Recipe | Does |
|---|---|
| `just setup` | Clones the project and `@project@-walk` beside this folder if they are missing, and checks for the skill. Run it first in a fresh clone |
| `just present` | Opens the walk on the project, with these notes and slides and the clock. `just present ID` opens another walk of `toc.toml` |
| `just check` | Checks the notes and the slides of every walk against the steps, and a tutorial's moves. With `toc.toml`, it then checks the pages that students read |
| `just style` | Checks the prose of the class against the writing guide of the walk skill. Its `scripts/style.py` names the files |
| `just pages` | Makes the pages that students read, for every walk of `toc.toml`, in `@project@-walk`, or in `build/pages` without it. Commits nothing |
| `just follow` | Follows each Build it yourself page in a scratch clone, as a student would. Every `git check` must pass. With Claude Code, a model also checks the text against the output, into `reports/follow/` |
| `just draft ID` | Drafts the notes of the moves of a tutorial from its commits. `just draft ID --write` adds them to its notes |
| `just pdf` | Makes `build/@project@.pdf`, the slides, one page each, for you and for the students. The notes are not in it. `just pdf ID` makes the PDF of another walk |
| `just check-pdf` | Checks that no slide is cut off in that PDF |
| `just walk-init` | Makes `@project@-walk`, once. Asks before it creates the public repository |
| `just walk-update` | Refreshes `@project@-walk` from the notes and the slides of every walk, and makes the pages that students read. Shows the diff, and commits on a yes. Never pushes |

The scripts behind `just style`, the pages part of `just check` and the last three recipes are the walk skill's, in `~/.agents/skills/walk`. Do not
copy them here.
