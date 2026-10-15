---
title: Make a class
---

This page goes from a project with step tags to a class that you can present. Your agent can do each part when you
ask it. The commands show what happens.

## The history

timewalk needs one commit and one annotated tag for each step. The message of the tag is a short title, a blank
line, and a sentence or two. Push the tags, because the class clones the project from GitHub:

```bash
git push origin main --tags
```

A tutorial also stops at each small commit between two tags. Each such commit is a move, and timewalk names it by
its place, for example `step-02.1`. The last move of a step carries the tag of the step. Keep the history on one
straight line. Make each move one small change, such as one test or one command.

## Make the class folder

```bash
python3 ~/.agents/skills/walk/scripts/class_init.py --project bla --upstream you \
    --repo ~/Projects/bla --dir ~/Projects/bla-class --toc
cd ~/Projects/bla-class
just setup
just walk-init
```

`class_init.py` writes `notes.md` with a section for each step tag, `slides/slides.example.toml`, the justfile, a
README and `toc.toml`. It commits, and then asks before it creates the private repository `you/bla-class` on
GitHub. `just setup` clones the project and the walk repository beside the class folder, if they are missing.
`just walk-init` makes `bla-walk`, and asks before it creates the public repository on GitHub.

## The walks

A walk is one path through the history, with its own notes and slides. `toc.toml` lists the walks of a class,
and the first one is the default. A walk is one of these kinds:

- **A narrative** goes from tag to tag. The class looks at each step whole.
- **A tutorial** also stops at each move. In do mode, the learner makes each move by hand. In watch mode, timewalk
  shows the commit of each move.
- **A small walk** takes some steps and moves out of a big tutorial, and shares its notes. You write each section
  once.

Here is a tutorial and a small walk out of it, from the class timewalk-test:

```toml
[[walk]]
id = "tutorial"
title = "tally, one move at a time"
kind = "tutorial"
folder = "walks/tutorial"           # its notes.md, and slides/slides.toml
loose = ["pyproject.toml", "uv.lock"]

[[walk]]
id = "small"
title = "Two parts of tally, one move at a time"
kind = "tutorial"
notes = "walks/tutorial/notes.md"   # the notes of the whole tutorial
slides = "walks/tutorial/slides/slides.toml"
intro = "walks/small/intro.md"
select = [{ range = "step-02.2..step-02.3", title = "An empty text, and case" }, "step-05.1"]
```

In do mode, timewalk compares the learner's files with the files of each move. A learner who runs `uv add` on a
later day gets newer versions, so `pyproject.toml` and `uv.lock` never match. So a tutorial with such a move sets
`loose`, and timewalk compares those files by the names of their packages, and not by their versions.

A small walk can also have notes of its own, with lines such as `{{include step-02.1}}` that take move sections from
the big tutorial. [Several walks](https://rahuldave.com/timewalk/walks.html) in timewalk's documentation lists every
key.

## Notes and slides

Each step has a section `## step-NN Title` in the notes. A tutorial also has a section `### step-NN.k Title` for each
move. `just draft tutorial --write` adds a draft section for each move that the notes do not have. Finish each draft by
hand.

A move section opens with the problem, gives the change piece by piece, and ends with a command that checks
it. The notes never copy the code of a file. A line `do$ COMMAND` gives the command that writes a file, and a line
`patch$ PATH` says that the move changes `PATH` by its patch.

A student who builds the project never commits. So write `rm` and `mv` on a `do$` line, not `git rm` and `git mv`. A
`git rm` of a file that the walk changed fails, and so does a `git mv` of a file that the walk made. `just check` names
each `git rm` and `git mv` of a tutorial as a problem.

`slides/slides.toml`, the manifest, says which slides show at each step. Once `slides.example.toml` gives every step
a slide, rename it to `slides.toml`. Then take the `#` off the line `slides = "slides/slides.toml"` in `toc.toml`.
timewalk does not start on a manifest that misses a step.

## Present

```bash
just present             # the first walk, with the clock
just present tutorial    # another walk
```

`just present` prints an address. Open it, and click **Room** to open the window for the projector. The Room
window hides your private cues, the lines of the notes such as `> Say:` that are for you alone. To change the notes, click **Edit** in the notes column, or edit the file in your editor.

## Send it to the students

Turn on GitHub Pages once for `bla-walk`, before its first push. In its settings on GitHub, under **Pages**, set
the source to **GitHub Actions**. Then:

1. Run `just check`, and fix every error. [Check a class](check.md) lists the other checks.
2. Run `just walk-update`. It copies the notes without your cues and the slides into `bla-walk`, and makes the pages
   that students read. It shows the diff, and asks before it commits.
3. Push `bla-walk`. The push also publishes its website.
