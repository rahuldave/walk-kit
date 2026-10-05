---
name: walk
description: Make and keep up a timewalk class for a project with one tagged commit for each step. Use it to make the private class material, PROJECT-class. Use it to make the public walk repository that students fork, PROJECT-walk, and to refresh it without the private cues. Use it to make the teacher's handout and the students' PDF.
---

# walk: a class that replays a project, step by step

A walk uses three repositories for a project called `bla`:

| Repository | Holds | Who sees it |
|---|---|---|
| `bla` | The project. One commit and one annotated tag `step-NN` for each step | Public |
| `bla-class` | The notes with private cues, the slides, the recipes | Private |
| `bla-walk` | The walk: the notes without private cues, the slides, a justfile | Public. Students fork it |

The scripts are in this skill's `scripts/` folder. They take the project, the owner and the paths as
arguments, and hold no project name. Run them with `python3`, from any folder.

## Before you start

Check that these are on the machine, and say which are missing:

- **uv** runs timewalk from GitHub, and gives Python. Check it with `uv --version`
- **just** runs the recipes. Check it with `just --version`
- **git**, and **gh** logged in to GitHub, make the repositories. Check with `gh auth status`
- **Chrome or Edge**, for the PDFs. Without them: `uvx playwright install chromium`
- **Python 3.10 or later** as `python3`, for the scripts. They use only the standard library

timewalk is not pinned. Every run fetches the newest from GitHub. `TIMEWALK` names another source,
for example a working copy.

The project must have its step tags on GitHub. `git push origin main --tags` puts them there.

## Tasks

1. **Make the class material.**

   ```
   python3 SKILL_DIR/scripts/class_init.py --project bla --upstream OWNER --repo ~/Projects/bla --dir ~/Projects/bla-class
   ```

   It writes `notes.md` with one section for each step tag, and `slides/slides.toml`. It also writes the
   justfile, a `.gitignore` for `build/`, `README.md`, and `AGENTS.md` with a `CLAUDE.md` that reads it.
   It commits, then asks before it creates the private repository `OWNER/bla-class`.

2. **Get the parts beside it.** In the class folder, run `just setup`. It clones the project and the
   walk repository beside the class folder if they are missing, and says if this skill is not installed. Run it
   first in every fresh clone of a class folder.

3. **Make the walk repository.** In the class folder, run `just walk-init`. It asks before it creates the public
   repository `OWNER/bla-walk`.

4. **Keep the walk repository up to date.** In the class folder, run `just walk-update`. It copies
   `slides/` when there is a `slides/slides.toml`. Add `--pdf` to ship `bla.pdf`. It shows the diff, and commits on a yes. It never pushes.

5. **Make the PDFs** in the class folder. They go into `build/`, which git ignores.
   - `just handout` makes `build/bla-handout.pdf`, with the private cues, for the teacher
   - `just student-pdf` makes `build/bla-student.pdf`, without them, to give to students

## The private lines

`scripts/private.py` is the one place that names them. A line that starts with `> Say:` or `> Note:`, and
a line `time: m:ss`, stay in the class material. Every other line goes to students, other `> ` cues
included. To show a cue to students, start it with another word, for example `> Try:`.

## Rules

- **Ask before you create a repository on GitHub, before every commit, and before every push.**
- **Rehearse every command** of the notes at its step in the replay copy before it goes into the notes.
- **Never write `walk.pdf` in a walk repository.** It is the student's own PDF, and its `.gitignore`
  lists it.
- **Keep paths out of the class justfile.** It finds the project as `../PROJECT` and the walk repository
  as `../PROJECT-walk`. `PROJECT_DIR` and `WALK_DIR` name other folders for one machine.
- **Do not copy the scripts** into a class folder. The class justfile calls them here, through
  `~/.agents/skills/walk`, or the folder that `WALK_SKILL` names.
