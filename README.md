# walk-kit

walk-kit makes a class out of a project's history. The project has one commit and one annotated tag for each step.
[timewalk](https://rahuldave.com/timewalk/) replays those steps in a browser, with the files, terminals and notes of
each step. walk-kit makes the repositories that a class needs beside the project, and keeps them up to date.

It is the walk skill for Claude Code, Codex and other coding agents. It is also a set of scripts and `just` recipes
that you can run yourself. For a project called `bla`, it makes these:

- `bla-class`, a private folder with your notes, your slides and the recipes
- `bla-walk`, a public repository that students fork. It has a copy of your notes without your private lines
- the pages that students read on GitHub and on a website, and a PDF of the slides

The documentation is at **[rahuldave.com/walk-kit](https://rahuldave.com/walk-kit/)**.

## Install

You need [uv](https://docs.astral.sh/uv/), [just](https://just.systems/), git, the
[GitHub CLI](https://cli.github.com/) logged in, Python 3.11 or later, and Chrome or Edge for the PDFs. Clone the
repository, and link it where your agents look for skills:

```
git clone https://github.com/rahuldave/walk-kit ~/Projects/walk-kit
mkdir -p ~/.agents/skills ~/.claude/skills ~/.codex/skills
ln -s ~/Projects/walk-kit ~/.agents/skills/walk
ln -s ../../.agents/skills/walk ~/.claude/skills/walk      # Claude Code
ln -s ../../.agents/skills/walk ~/.codex/skills/walk       # Codex
```

Then ask your agent to make a class for a project, or follow
[Make a class](https://rahuldave.com/walk-kit/make-a-class.html).

## Private cues

timewalk shows every line of a notes file. So `just walk-update`, which copies your notes into `bla-walk`, leaves
out your private lines. A private line starts with `> Say:` or `> Note:`, or is a planned time, `time: m:ss`. The
`>` lines around such a line are private too, up to a blank line. [The three repositories](https://rahuldave.com/walk-kit/repositories.html#private-cues)
gives the exact rules. `scripts/private.py` is the one place in the code that names them.

## Work on walk-kit

`just test` makes the pages of the walks of [timewalk-test](https://github.com/rahuldave/timewalk-test). Then it runs
the commands of each Build it yourself page in a scratch clone, and fails if a `git check` fails. `just style` checks
this README and `templates/walk/README.md` against the writing guide, and then has a model review them. `just docs` builds the
documentation from `docs/` and serves it at http://127.0.0.1:8001.

Agents read [SKILL.md](SKILL.md) and [WALKS.md](WALKS.md). The writing guide is [style/GUIDE.md](style/GUIDE.md).

## Licence

MIT. See [LICENSE](LICENSE).
