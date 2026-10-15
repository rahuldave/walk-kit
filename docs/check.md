---
title: Check a class
---

A class goes wrong in small ways. For example, a tag moves, or a page shows an output that its command no longer
prints. Each check below finds one kind of mistake. Run them in the class folder, before `just walk-update`.

| Recipe | What it checks | Calls a model |
|---|---|---|
| `just check` | The notes and slides of every walk against the steps, then the pages that students read | No |
| `just pages` | Makes the pages, with the same checks as `just walk-update`, and commits nothing | No |
| `just follow` | Each Build it yourself page, followed in a scratch clone | Yes, with Claude Code |
| `just style` | The prose of the class against the writing guide | Yes, with Claude Code |

`just follow` and `just style` call Claude Code through `claude -p`, with the model Opus. Each call counts against
your Claude plan, or costs money on an API key. Without Claude Code, both recipes skip the call and run the rest.

## just check

`just check` runs `timewalk-check` on every walk. It checks each section of the notes and each slide entry against
the steps, and each item under `files:` against the change of its move. It runs the `do$` lines of each move in a
scratch clone, to see which files they write. It warns of a file that no `do$` line writes and no `patch$` line
names. An error stops `just present` too, so fix every error, and read every warning.

Then, in a class with `toc.toml`, it renders the pages in a temporary folder and checks them. A page that breaks the
writing guide is a problem. So is a page that cannot say which files its `do$` lines write, because they did not run. Words such as "step" and
"commit" in the text that a student reads give a warning.

## just pages

`just pages` writes the pages, and commits nothing. With a walk repository, it writes them into `bla-walk`, and a later
`just walk-update` commits them. Without one, it writes them into `build/pages`.

## just follow

`just follow` makes the pages, and then does what a student would do. For each Build it yourself page, it clones
the project into a scratch folder and runs every command of the page in order. A `curl` of a diff on GitHub becomes
the same `git diff` in your local project. A command that fails is logged, because some notes run a failing test
on purpose. But each `git check` after a move must print nothing. The log of each page goes to `build/follow/ID.md`.

With Claude Code, a model then reads the page and its log once. It reports each output, number or claim of the text
that the log does not show. Its report goes to `reports/follow/ID-build.md`, and each run writes it again. A finding
fails the recipe. Fix the notes, and run it again.

## just style

`just style` checks the README, the notes, the intros and the slides, which people outside the class read. It
skips `AGENTS.md` and `CLAUDE.md`, which are for agents.

1. `style/check.py` checks the form, such as the length of a sentence, a dash or a colon between two clauses. Fix
   every hard problem. `just style -v` also shows the soft notes, for you to judge.
2. When the form passes, a model reviews the text that changed since the last commit, or a new file whole. It reports where a reader
   would stumble, with a rewrite. A text that passed is kept in a cache, so a second run of the same text costs
   nothing.

The model checks each fact of the notes against the project as it was at that point of the walk. For example, the
section `### step-02.1` speaks of the first commit of step-02. A file that step-05 makes does not exist there yet.

Before the text, the model gets a table that gives each section of the notes its commit. A section `## step-NN` has
the tag step-NN, and `### step-NN.k` the move's commit. A stop of a walk with notes of its own has the commits of its
`{{include ...}}` lines. The model reads the files at that commit with `git show`, and may run no other command.

The model never sees your own cues. walk-update leaves the lines `> Say:`, `> Note:` and `time: m:ss` out of the walk
repository, so students never read them. The review leaves out the same lines. A change to those lines alone is not
reviewed.

The model cannot run a command, so it never changes what a command prints. For example, the notes say that
`uv run ruff format --check` prints `5 files already formatted`. The model keeps the number 5. `just follow` runs
the commands, and its model checks their output.

The findings of each file go to `reports/writing/`, at the path of the file with `.md` added. Under each finding
that you fix, write a line `- Fixed: ...`. A finding without that line is left for the owner of the class. A file is
reviewed at most three times between two commits. The first two reviews fail on a finding. The third passes, and leaves its findings for you to judge.

Git ignores `reports/writing/` and `reports/follow/`. It tracks any other report in `reports/`.

More rounds make the prose
stiff, so rewrite by hand instead.

### Review whole files with --all

`just style` reviews only the text that changed since the last commit. So text that was written before the class took up
the review is never reviewed. `just style --all` has the model review each file whole. Run it once, when a class takes
up the review, and again after big edits. It costs one review of each file. The limit of three reviews of a file between
two commits holds for `--all` too.
