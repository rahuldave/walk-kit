# The walk through @project@

@project@ grew in steps, with one commit and one tag for each step. This repository replays the class with
[timewalk](https://rahuldave.com/timewalk/). At every step, the page shows the files as they were and what
the step changed. It also has terminals in the repository at that step, and the notes of the step with
their commands.

## Read it without timewalk

If this repository has a `toc.toml`, each walk is also a set of pages, to read on GitHub or on its website. There are two ways to
read a tutorial. **Read the tutorial** explains each change, with the code to look at. **Build it yourself** gives
every command to run and every patch to apply, so that you make the project yourself. Each part of the pages ends
with **What changed**. It lists every file of the change, with a link to the file and its whole diff.

Build it yourself needs no timewalk. You make a new clone of @project@ for it, and the pages
give every command to run in it. They also show how to add a command to that clone, `git check`, which tells
you after each change whether your files match the project's.

[The pages on GitHub](walks/README.md) list each walk with its two ways of reading. The same pages are a website,
[@upstream@.github.io/@project@-walk](https://@upstream@.github.io/@project@-walk/).

## What you need

- [uv](https://docs.astral.sh/uv/), which also runs timewalk from GitHub
- [git](https://git-scm.com/)
- [just](https://just.systems/), which runs the recipes of this repository
- Chrome, Edge or another recent browser

## Start

1. Fork this repository on GitHub, so that you can save your own notes. Then clone your fork.
2. In its folder, run `just present`.
3. Open the address that timewalk prints.

```
git clone https://github.com/<you>/@project@-walk
cd @project@-walk
just present
```

`just present` runs `just setup` first. The first time, `just setup` clones @project@ into `repo/`. If you
also forked @project@, it clones your fork, so that you can push your own work. Otherwise it clones
`@upstream@/@project@`. Every time, it fetches the tags of the steps from `@upstream@/@project@`.

timewalk then puts its replay copy in `worktree/`. The replay copy is a clone of `repo/` on the branch
`timewalk/replay`, which timewalk moves from step to step. timewalk never writes to `repo/`. A `worktree/` that
an older timewalk made is a git worktree, which keeps its records in `repo/.git/worktrees`. Git ignores both
folders, so they never enter your fork. To clone from another address, run `just setup <address>` before the
first `just present`.

## The folders

```
@project@-walk/
├── walk.md        the notes of every step, tracked in your fork. With toc.toml, the notes that it names
├── toc.toml       only with several walks: the list of walks, and where the notes of each are
├── walks/         the pages of each walk to read on GitHub, walks/ID/read.md and walks/ID/build.md
├── site/, sites/  the same pages as a website, which the Pages workflow publishes
├── slides/        the slides, and slides.toml, which says which slides show at which step
├── justfile       the recipes: present, setup, pdf
├── repo/          ignored: your clone of @project@
└── worktree/      ignored: the replay copy
```

## Several walks

If this repository has a `toc.toml`, it has several walks. `just present` opens the first, and
`just present ID` opens the walk with that id. The menu at the left of the step bar changes the walk.

A walk is a narrative or a tutorial. A narrative goes from step to step. A tutorial also has moves, the
small commits between two steps.

In do mode, you make each move by hand from its notes, run the command at
its end, and press **Done**. A patch in the notes has a button, **Apply patch**, that applies it to your file. **Catch me up** sets the code to the end of the move. In watch mode, **Show**
checks out each move. The moves of a step go in order. To go back, press **Restart step**, and then run
`just setup`.

## The page

- **The notes column** on the right shows the notes of the step. A click on a command types it into its
  terminal. Read the command, and then press Enter to run it. To run a command with one click, turn on
  **run on click**.
- **Edit** at the top of the notes column changes the notes of the step. They are in `walk.md`, or in the notes
  that `toc.toml` names. Commit that file to your fork to keep your notes.
- **At this step** and **Runs** are terminals in `worktree/`, at the step. The notes of each step start
  with `$ just setup`. The command runs the project's own recipe, at the step, and makes the environment
  of the step. It is not the `just setup` of this repository.
- **A move keeps your work.** Before a move to another step, timewalk keeps your edits and commits in
  `worktree/` on a branch `timewalk/saved/<step>`, and does not ask. The page names the branch, and gives
  the command that brings a file back. A `worktree/` from an older timewalk is a git worktree, and there a move
  with edits asks and stashes them. To change it, keep what you need from `worktree/`, delete the folder, run
  `git -C repo worktree prune`, and run `just present` again.
- **Main** is a terminal in `repo/`, your clone of @project@. A move never touches it. Work there on
  `main`, commit, and push to your own fork.
- **PDF** makes a PDF of the slides, one page each. The notes are not in it. They are for this page. `just pdf`
  makes the same file, `build/walk.pdf`. Git ignores `build/`, so your own PDF never changes your fork. This
  repository may also ship `@project@.pdf`, the PDF of the walk as written.
