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

A walk is one path through the steps, with its own notes and slides. A narrative goes from tag to tag. A
tutorial also stops at each move, a small commit between two tags, and the class makes each move in turn.
A class has one walk, or several listed in `toc.toml`. [WALKS.md](WALKS.md) says what each kind needs.

## What you need

- [uv](https://docs.astral.sh/uv/), which runs timewalk from GitHub
- [just](https://just.systems/), which runs the recipes
- [git](https://git-scm.com/), and the [GitHub CLI](https://cli.github.com/), `gh`, logged in
- Chrome or Edge, for the PDFs
- Python 3.10 or later, as `python3`. The scripts use only the standard library. A class with `toc.toml`
  needs 3.11

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
just walk-update        # refresh bla-walk from the notes and slides of every walk
just present            # open the walk, with your notes and the clock. just present ID opens another walk
just check              # check the notes and slides of every walk against the steps
just draft ID           # draft the notes of a tutorial's moves; add --write to put them in its notes
just pdf                # build/bla.pdf: the slides, one page each. The notes are for the step browser
BRAND=brand/x just pdf  # the same, with the look of the brand folder brand/x: font, colours, cover, dividers
just check-pdf          # check that no slide is cut off in it
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
| Which slides show at which step | `slides/slides.toml`. `class_init.py` writes `slides/slides.example.toml`: rename it once it has every step |
| The list of walks, in a class with several | `toc.toml`. `class_init.py --toc` writes it |
| Each walk after the first | `walks/ID/notes.md` and `walks/ID/slides/` |

1. **Open the walk.** Run `just present` in `bla-class`, and open the address that it prints.
2. **Edit the notes.** On the page, click **Edit** in the notes column, and then **Save**. Or edit
   `notes.md` in your editor. The page reads it again at the next move.
3. **Edit the slides** in your editor. timewalk reads the slide files again each time it shows a slide.
4. **Try each command** in the **At this step** terminal before it goes into the notes. Then run `just check`.
5. **Read the PDF.** `just pdf` makes it: the slides, one page each, for you and for the students. The notes are not in it; they are for the step browser. `just check-pdf` checks that no slide is cut off.
6. **Commit and push `bla-class`.** It is private.
7. **Send it to the students.** `just walk-update` copies the notes and the slides into `bla-walk`, shows
   the diff, and asks before it commits. Then push `bla-walk`.

timewalk's documentation describes the [notes](https://rahuldave.com/timewalk/notes.html), the
[slides](https://rahuldave.com/timewalk/slides.html), the [page](https://rahuldave.com/timewalk/page.html),
and [several walks](https://rahuldave.com/timewalk/walks.html).

## The version of timewalk

timewalk is not pinned. Every recipe and script runs the newest commit of timewalk on GitHub, and fetches
it again at each start, which takes about a second. `scripts/common.py` names the source. On the branch
`walks` of walk-kit, it is timewalk's branch `walks`. To run another copy, for example a working copy that
you are changing, set `TIMEWALK` to its folder:

```
TIMEWALK=~/Projects/timewalk just present
```

## Private cues

timewalk shows every line of a notes file. So the notes that students get leave out your private lines. A private line starts with `> Say:` or
`> Note:`, in any case and with emphasis too, such as `> **Say:**`, or is a planned time, `time: m:ss`, also when it is indented.
The whole blockquote of a cue goes with it: every `>` line around it, a line of `>` alone too, and the lines that go on
without a `>`, up to a blank line. A blockquote with a private cue and a public cue, such as `> Try:` or `> Fast:`, stops
`just walk-update`: put a blank line between the two. When a cue sits in an HTML comment, its `-->` stays. A line in
fenced code is code, and stays. `scripts/private.py` is the one place that says so.

`just walk-update` writes only into the walk repository. It refuses a walk repository that is the class folder or the
project, or that is inside or around either, by any spelling of the folder: the disk decides. It refuses a walk
repository whose `.git` is a file, a worktree or a submodule. It refuses a path in `toc.toml` that is absolute or has a
`..`, or that would take the place of a file of the walk repository, such as `README.md` or `repo/`. It refuses a
`toc.toml` with a private line in a value, such as a `description`. It writes each file as a new file, so a link in the
walk repository is replaced, and never written through.

It also writes the walk repository's `justfile`, `README.md`, `AGENTS.md`, `CLAUDE.md` and `.gitignore` again from
the templates of walk-kit, so an old walk repository gets the new recipes. The upstream owner is `--upstream`, which the
class justfile gives, or else the one that the old `justfile` names. A file that matches no version of the template was
edited by hand: `just walk-update` says so, and the diff shows what goes.

It copies the folder of each slides manifest whole, and nothing else of the class folder. So it refuses a manifest in
the class folder itself, or in a folder that holds the notes of a walk. It refuses a symbolic link in a slides folder
or for the notes, a PDF whose name is not the file of an entry of the manifest, and a slide with a private line. Before
it offers to commit, it checks every file that the commit would take, not only those that it wrote. A line in fenced code that would be private outside it, such as an example `> Say:`,
also stops it: if the line is code for students, run `just walk-update --allow-cues-in-code`.

## Licence

MIT. See [LICENSE](LICENSE).
