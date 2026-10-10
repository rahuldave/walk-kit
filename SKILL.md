---
name: walk
description: Make and keep up a timewalk class for a project with one tagged commit for each step. Use it to make the private class material, PROJECT-class, with one walk or several, narratives and tutorials. Use it to make the public walk repository that students fork, PROJECT-walk, and to refresh it without the private cues. Use it to make the PDF of the slides.
---

# walk: a class that replays a project, step by step

A walk uses three repositories for a project called `bla`:

| Repository | Holds | Who sees it |
|---|---|---|
| `bla` | The project. One commit and one annotated tag `step-NN` for each step | Public |
| `bla-class` | The notes with private cues, the slides, the recipes | Private |
| `bla-walk` | The walk: the notes without private cues, the slides, a justfile | Public. Students fork it |

A walk is one path through the steps, with its own notes and slides. A narrative goes from tag to tag. A
tutorial also stops at each move, a small commit `step-NN.k:` between two tags. A class has one walk, or
several listed in `toc.toml`. **Read [WALKS.md](WALKS.md) before you write the notes of a walk, or add a walk.**
It holds the rules of `just setup`, of the history and of a tutorial's notes.

The scripts are in this skill's `scripts/` folder. They take the project, the owner and the paths as
arguments, and hold no project name. Run them with `python3`, from any folder.

## Before you start

Check that these are on the machine, and say which are missing:

- **uv** runs timewalk from GitHub, and gives Python. Check it with `uv --version`
- **just** runs the recipes. Check it with `just --version`
- **git**, and **gh** logged in to GitHub, make the repositories. Check with `gh auth status`
- **Chrome or Edge**, for the PDFs. Without them: `uvx playwright install chromium`
- **Python 3.10 or later** as `python3`, for the scripts. They use only the standard library. A class with
  `toc.toml` needs 3.11, which reads TOML

timewalk is not pinned. Every run fetches the newest from GitHub. `TIMEWALK` names another source,
for example a working copy. On this skill's branch `walks`, `scripts/common.py` names timewalk's branch
`walks`, which has the walks and the tutorials.

The project must have its step tags on GitHub. `git push origin main --tags` puts them there.

## Tasks

1. **Make the class material.**

   ```
   python3 SKILL_DIR/scripts/class_init.py --project bla --upstream OWNER --repo ~/Projects/bla --dir ~/Projects/bla-class
   ```

   It writes `notes.md` with one section for each step tag, and `slides/slides.example.toml`. Rename that file
   to `slides.toml` once it has a line for every step: a manifest that misses a step is an error. `--toc` also writes
   `toc.toml`, for a class with several walks. It also writes the justfile, a `.gitignore` for `build/`,
   `README.md`, and `AGENTS.md` with a `CLAUDE.md` that reads it.
   It commits, then asks before it creates the private repository `OWNER/bla-class`.

2. **Get the parts beside it.** In the class folder, run `just setup`. It clones the project and the
   walk repository beside the class folder if they are missing, and says if this skill is not installed. Run it
   first in every fresh clone of a class folder.

3. **Make the walk repository.** In the class folder, run `just walk-init`. It asks before it creates the public
   repository `OWNER/bla-walk`.

4. **Write and check the walks.** In the class folder, `just present` opens the first walk, and
   `just present ID` another. `just check` checks every walk against the steps. `just draft ID` drafts the
   notes of a tutorial's moves, and `just draft ID --write` adds them. WALKS.md gives the order of the checks.

5. **Keep the walk repository up to date.** In the class folder, run `just walk-update`. It copies the notes
   and the slides of every walk, and `toc.toml` if there is one. It copies the folder of each manifest whole, and
   refuses a manifest in the class folder itself or beside the notes of a walk. It writes only into the walk repository,
   and refuses a `--walk` that is the class folder or the project by any spelling, a worktree or a submodule, or a path of
   `toc.toml` with a `..`. It writes the walk repository's justfile, README.md, AGENTS.md, CLAUDE.md and .gitignore again
   from the templates, and says when one was edited by hand. Before the commit, it checks every file that the commit
   would take. Add `--pdf` to ship `bla.pdf`, and `bla-ID.pdf` for each
   other walk with slides. It shows the diff, and commits on a yes. It never pushes.

6. **Make the PDF** in the class folder. It goes into `build/`, which git ignores.
   - `just pdf` makes `build/bla.pdf`, and `just pdf ID` makes `build/bla-ID.pdf`: the slides, one page
     each, for the teacher and for the students. The notes are not in it. They are for the step browser, `just present`. A slide that is long is shrunk to
     fit its page
   - `BRAND=brand/NAME just pdf` gives the PDF the look of a brand: a folder in the class folder with a `brand.toml`,
     a logo and fonts. A class can keep several. Without `BRAND`, the PDF has no brand. The keys are in timewalk's
     docs, https://rahuldave.com/timewalk/brand.html
   - `just check-pdf` checks that no slide is cut off: the last words of every slide must be in the PDF's text

## The private lines

`scripts/private.py` is the one place that names them. A line that starts with `> Say:` or `> Note:`, in any
case and with emphasis too, and a line `time: m:ss`, stay in the class material, also when they are indented. The
whole blockquote of a cue stays with it: its `>` lines, a line of `>` alone too, and the lines that go on without a
`>`, up to a blank line. A blockquote with a private cue and a public cue, such as `> Try:`, stops `walk-update`: put a
blank line between the two cues. The `-->` of an HTML comment around a cue stays. A line in
fenced code is code, and goes to students. But `walk-update` stops on a line in code that would be private outside
it, until `--allow-cues-in-code` says that it is code to show. Every other line goes to students, other `> ` cues
included. To show a cue to students, start it with another word, for example `> Try:`.

## Rules

- **List the files a move or a step changed, never in prose.** Write "These are the files changed:", then one
  item for each file: its path in code, then what happened to it. WALKS.md shows the shape.
- **Ask before you create a repository on GitHub, before every commit, and before every push.**
- **Rehearse every command** of the notes at its step, or its move, in the replay copy before it goes into the notes.
- **Every command runs through `uv run` or a `just` recipe,** never a bare `python`. Each step's notes start
  with `$ just setup`, which never touches git.
- **Never write `build/walk.pdf` in a walk repository.** It is the student's own PDF, and its `.gitignore`
  lists `build/`.
- **Keep paths out of the class justfile.** It finds the project as `../PROJECT` and the walk repository
  as `../PROJECT-walk`. `PROJECT_DIR` and `WALK_DIR` name other folders for one machine.
- **Do not copy the scripts** into a class folder. The class justfile calls them here, through
  `~/.agents/skills/walk`, or the folder that `WALK_SKILL` names.
