---
title: walk-kit
subtitle: A class from the history of a project
---

You can teach a project by building it again in front of the class, one step at a time. A step is one commit of
the project, with an annotated tag, `step-01`, `step-02` and so on.
[timewalk](https://rahuldave.com/timewalk/) then replays the steps in a browser. It shows the files of each step and
what the step changed. It also shows your notes, your slides, and a terminal in the project as it was then.

A class needs more than the history. You need notes with cues that only you see, and slides. The students need a
copy of the notes without your cues, and pages that they can read at home. And when you change a commit between
classes, the notes, the slides and the pages have to change with it.

walk-kit is the walk skill for Claude Code, and for Codex and other coding agents. It is also a set of Python
scripts, and recipes for [just](https://just.systems/), a command runner. You can run both yourself. It makes these things for a project called `bla`:

- **`bla-class`**, a private folder with your notes, your slides and the recipes that use them
- **`bla-walk`**, a public repository that students fork. It has the notes without your cues, the slides, and a
  justfile that opens timewalk
- **the pages that students read**, on GitHub and on a website. A tutorial gets two ways of reading,
  **Read the tutorial** and **Build it yourself**
- **a PDF of the slides**, one slide on each page

## Install

You need [uv](https://docs.astral.sh/uv/), [just](https://just.systems/), git, the
[GitHub CLI](https://cli.github.com/) logged in, Python 3.11 or later as `python3`, and Chrome or Edge for the PDFs.
The scripts use only the standard library of Python.

Clone walk-kit, and link it where your agents look for skills:

```bash
git clone https://github.com/rahuldave/walk-kit ~/Projects/walk-kit
mkdir -p ~/.agents/skills ~/.claude/skills ~/.codex/skills
ln -s ~/Projects/walk-kit ~/.agents/skills/walk
ln -s ../../.agents/skills/walk ~/.claude/skills/walk      # Claude Code
ln -s ../../.agents/skills/walk ~/.codex/skills/walk       # Codex
```

The recipes of a class find the scripts in `~/.agents/skills/walk`. To keep walk-kit in another folder, set the
environment variable `WALK_SKILL` to that folder.

## Use it

Ask your agent to make a class for a project, for example "Make a timewalk class for ~/Projects/bla". The agent
reads the skill, runs the scripts, and asks you before it creates a repository on GitHub or commits. Or run the
scripts and the recipes yourself, as [Make a class](make-a-class.md) shows.

## Read on

- [The three repositories](repositories.md) says what goes where, and what never reaches the students.
- [Make a class](make-a-class.md) goes from a tagged project to a class that you can present.
- [The pages that students read](student-pages.md) shows what a student gets without timewalk.
- [Check a class](check.md) lists the checks, and says which of them call a model.
- [Recipes](recipes.md) lists every recipe of a class and of walk-kit.

timewalk has its own documentation, at [rahuldave.com/timewalk](https://rahuldave.com/timewalk/). It describes the
[notes](https://rahuldave.com/timewalk/notes.html), the [slides](https://rahuldave.com/timewalk/slides.html) and
[several walks](https://rahuldave.com/timewalk/walks.html). The class
[timewalk-test](https://github.com/rahuldave/timewalk-test) is a worked example of every part of walk-kit.
