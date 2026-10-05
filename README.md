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
| `bla-walk` | The kit: the notes without private cues, the slides, and a justfile | Public. Students fork it |

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
just setup              # clone the project and the kit beside this folder, if missing
just walk-init          # make the kit, bla-walk
just walk-update        # refresh the kit from notes.md
just present            # open the walk, with your notes and the clock
just handout            # build/bla-handout.pdf, with your private cues
just student-pdf        # build/bla-student.pdf, without them
```

The class justfile finds the project and the kit beside the class folder, as `../bla` and `../bla-walk`.
So a clone of the class folder on another machine needs only `just setup`. To keep them somewhere else,
set `WALK_REPO` and `WALK_KIT`.

Every script that creates a repository on GitHub asks first. `walk-update` shows the diff and asks before
it commits. No script pushes a kit.

## Private cues

timewalk shows every line of a notes file. So the notes that students get leave out your private lines. A private line starts with `> Say:` or
`> Note:`, or is a planned time, `time: m:ss`. `scripts/private.py` is the one place that says so.

## Licence

MIT. See [LICENSE](LICENSE).
