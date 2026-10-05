# walk-kit

walk-kit makes a class out of a project's history. The project has one commit and one tag for each step.
[timewalk](https://rahuldave.com/timewalk/) replays those steps in a browser, with the files, terminals
and notes of each step. walk-kit makes the repositories around it, and keeps them up to date.

It is a skill for Claude Code, Codex and other coding agents, and a set of scripts that you can run
yourself.

## The three repositories

| Repository | Holds | Who sees it |
|---|---|---|
| `bla` | The project. One commit and one annotated tag `step-NN` for each step | Public |
| `bla-class` | Your notes with private cues, the slides, and the recipes | Private |
| `bla-walk` | The walk: the notes without private cues, the slides, and a justfile | Public. Students fork it |

## What you need

- [uv](https://docs.astral.sh/uv/), which runs timewalk from GitHub
- [just](https://just.systems/), which runs the recipes
- [git](https://git-scm.com/), and the [GitHub CLI](https://cli.github.com/), `gh`, logged in
- Chrome or Edge, for the PDFs
- Python 3.10 or later, as `python3`. The scripts use only the standard library

## Install

Clone the repository, and link it where your agents look for skills:

```
git clone https://github.com/rahuldave/walk-kit ~/Projects/walk-kit
mkdir -p ~/.agents/skills ~/.claude/skills ~/.codex/skills
ln -s ~/Projects/walk-kit ~/.agents/skills/walk
ln -s ../../.agents/skills/walk ~/.claude/skills/walk      # Claude Code
ln -s ../../.agents/skills/walk ~/.codex/skills/walk       # Codex
```

The class justfile finds the scripts in `~/.agents/skills/walk`. To keep them somewhere else, set
`WALK_SKILL` to that folder.

## Use it

Ask your agent to make a class for a project, or run the scripts yourself:

```
python3 ~/.agents/skills/walk/scripts/class_init.py --project bla --upstream you --repo ~/Projects/bla --dir ~/Projects/bla-class
cd ~/Projects/bla-class
just setup              # clone the project and bla-walk beside this folder, if missing
just walk-init          # make bla-walk, the repository that students fork
just walk-update        # refresh bla-walk from notes.md and slides/
just present            # open the walk, with your notes and the clock
just handout            # build/bla-handout.pdf, with your private cues
just student-pdf        # build/bla-student.pdf, without them
```

The class justfile finds the project and the walk repository beside the class folder, as `../bla` and
`../bla-walk`. So a clone of the class folder on another machine needs only `just setup`. To keep them
somewhere else, set `PROJECT_DIR` and `WALK_DIR`.

Every script that creates a repository on GitHub asks first. `walk-update` shows the diff and asks before
it commits. No script pushes the walk repository.

## Edit the notes and the slides

You edit everything in `bla-class`, and never in `bla` or `bla-walk`.

| What | Where |
|---|---|
| The script of each step | `notes.md`, one section for each step, `## step-NN Title` |
| The slides | `slides/*.md`, and the pictures beside them |
| Which slides show at which step | `slides/slides.toml` |

1. **Open the walk.** Run `just present` in `bla-class`, and open the address that it prints.
2. **Edit the notes.** On the page, click **Edit** in the notes column, and then **Save**. Or edit
   `notes.md` in your editor. The page reads it again at the next move.
3. **Edit the slides** in your editor. timewalk reads the slide files again each time it shows a slide.
4. **Try each command** in the **At this step** terminal before it goes into the notes.
5. **Read the PDFs.** `just handout` makes yours, with your cues. `just student-pdf` makes the students'.
6. **Commit and push `bla-class`.** It is private.
7. **Send it to the students.** `just walk-update` copies the notes and the slides into `bla-walk`, shows
   the diff, and asks before it commits. Then push `bla-walk`.

timewalk's documentation describes the [notes](https://rahuldave.com/timewalk/notes.html), the
[slides](https://rahuldave.com/timewalk/slides.html) and the [page](https://rahuldave.com/timewalk/page.html).

## The version of timewalk

timewalk is not pinned. Every recipe and script runs the newest commit of timewalk on GitHub, and fetches
it again at each start, which takes about a second. To run another copy, for example a working copy that
you are changing, set `TIMEWALK` to its folder:

```
TIMEWALK=~/Projects/timewalk just present
```

## Private cues

timewalk shows every line of a notes file. So the notes that students get leave out your private lines. A private line starts with `> Say:` or
`> Note:`, or is a planned time, `time: m:ss`. `scripts/private.py` is the one place that says so.

## Licence

MIT. See [LICENSE](LICENSE).
