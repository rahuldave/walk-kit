# The walk through @project@

@project@ grew in steps, with one commit and one tag for each step. This repository replays the class with
[timewalk](https://rahuldave.com/timewalk/). At every step, the page shows the files as they were and what
the step changed. It also has terminals in the repository at that step, and the notes of the step with
their commands.

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

timewalk then puts its replay copy in `worktree/`. The replay copy is a second working folder of the
same repository, which timewalk moves from step to step. Git ignores both folders, so they never enter
your fork. To clone from another address, run `just setup url=<address>` before the first `just present`.

## The folders

```
@project@-walk/
├── walk.md        the notes of every step, tracked in your fork
├── justfile       the recipes: present, setup, pdf
├── repo/          ignored: your clone of @project@
└── worktree/      ignored: the replay copy
```

## The page

- **The notes column** on the right shows the notes of the step. A click on a command types it into its
  terminal. Read the command, and then press Enter to run it. To run a command with one click, turn on
  **run on click**.
- **Edit** at the top of the notes column changes the notes of the step in `walk.md`. Commit `walk.md`
  to your fork to keep your notes.
- **At this step** and **Runs** are terminals in `worktree/`, at the step. timewalk starts with
  `--discard-edits`, so a move to another step throws away your edits there.
- **Main** is a terminal in `repo/`, your clone of @project@. A move never touches it. Work there on
  `main`, commit, and push to your own fork.
- **PDF** makes a PDF of the slides, one page each. The notes are not in it: they are for this page. `just pdf` makes
  the same file, `walk.pdf`. Git
  ignores `walk.pdf`, so your own PDF never changes your fork. This repository may also ship `@project@.pdf`, the
  PDF of the walk as written.
