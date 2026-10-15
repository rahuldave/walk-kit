---
title: The pages that students read
---

A student who misses a class, or wants to go over it again, may not have timewalk running. So `just walk-update`
also makes pages of each walk to read without it. They go into the walk repository, `bla-walk` for a project
called `bla`, as Markdown pages for GitHub and as a website. The pages are for a reader who has never heard of timewalk, so they never name its steps or commits.

The class timewalk-test shows the result, at [rahuldave.com/timewalk-test](https://rahuldave.com/timewalk-test/).

## Two ways of reading

A tutorial has two ways of reading, from the same notes:

- **Read the tutorial** explains each change, with the code to look at. It holds what watch mode shows. A command
  that made the change shows as a sentence, with nothing to run.
- **Build it yourself** gives every command to run and every patch to apply. The student makes the project in a
  clone of their own. It holds what do mode shows.

A narrative has Read the tutorial only.

Each part ends with a section **What changed**. It lists every file of the change, with what the notes say
of it, its counts of lines and a link to the file. Then comes the diff of each file, closed until the reader opens
it. Last come links to the change on GitHub and to the code after it. In Build it yourself, the patches to apply are open.

## Get the project, and git check

Build it yourself starts with **Get the project**. The student clones the project, and makes a branch at the
commit where the walk starts:

```bash
git clone https://github.com/o/tally
cd tally
git switch -c mine 6a63758166d3
```

The same section adds a git alias, `git check`. After each move, the page gives `git check` with the commit of the
move. It runs `git add -A` in a copy of git's index, so a new file counts too. The student's own index does not
change. It prints nothing when the student's files match.

A student who runs `uv add` a month later gets newer packages, and the files no longer match. For example, the
author's `uv add --dev ruff` wrote ruff 0.17.0, and the student's writes ruff 0.17.1. A walk handles this in one of
two ways. Its `loose` list in `toc.toml` chooses.

**Strict.** The walk's `loose` does not name `pyproject.toml` and `uv.lock`, or the walk has no `loose`. `git check`
compares every file line by line. So the page does not tell the student to run a `uv` command that writes
`pyproject.toml` or `uv.lock`, such as `uv add`, `uv remove` or `uv lock`. It says which command the author ran, and
gives one command in its place:

```bash
git restore --source 1a2b3c4d5e6f -- pyproject.toml uv.lock && uv sync --locked --all-groups --all-packages
```

`git restore` takes each file that the author's command wrote from the project, as the author has it after the
move. `uv sync --locked` installs exactly the versions that this `uv.lock` names, and does not change it.

`--all-groups` installs every group of dependencies, and `--all-packages` every package of a workspace, as the
author's `uv add --group` and `uv add --package` do. Without them, `uv sync` installs only the default groups. For
example, after the author's `uv add --group docs mdformat`, the student's `uv run mdformat` would fail.

A command such as `uv init` also writes other files, for example `.python-version`. The page takes them the same
way, and says so. A later command of the move can write one of these files, for example a `sed` that edits
`pyproject.toml`. That command does not run either. The student takes the file as the move ends.

To find the files that each command writes, `timewalk-export --json` runs each `do$` line in a scratch copy of the
project. The renderer reads the result from the JSON file that this command writes.

**Loose.** The walk's `loose` names `pyproject.toml` and `uv.lock`. The student runs the author's `uv add`, and gets
the newest versions. `git check` then compares these files as timewalk does:

- `pyproject.toml` and `uv.lock` are compared by the names of their packages, and not by their versions. **Get the
  project** writes a small Python program, `package_names.py`, into the folder `.git`. It is a copy of timewalk's own
  rules. git runs it through uv on each of these files, and compares what it prints.
- For example, the student's `uv add --dev ruff` writes `"ruff>=0.17.1"`, and the project has `"ruff>=0.17.0"`.
  `git check` prints nothing, because both files name the same packages.
- Any other file that `loose` names has to be there when the commit has it.

Dependencies and `uv.lock` change only through uv commands, on `do$` lines. `just check` names a `patch$` line that
changes the dependencies of a `pyproject.toml`, and every `patch$` line of a `uv.lock`.

## When a student is stuck

Each move has a command under "If you are stuck" that takes the files of the move. It puts the files of the commit
before the move in git's index first, so it deletes only what the move deletes. The student's other files stay.

A walk can skip changes between two parts. The part after such a gap starts with the same kind of command. It puts
the files that the part starts from in place of the student's files.

On the website, each part has a page, and a student can start at any of them. The page gives a command that puts
the files where the part starts into the student's clone. A file that the project deleted before the part stays,
and the page says to delete it if `git check` lists it.

In the notes, a line `patch$ PATH` says that a move changes `PATH` by a patch. In Build it yourself, the line
becomes a command that applies the patch from GitHub, with `curl` and `git apply`.

A `pyproject.toml` that `loose` names is the exception. Its line becomes a command that sets each value that the move sets, such as the table
`[tool.ruff]`, with tomlkit, a TOML library. The command keeps the rest of the student's file, and the versions that
the student's `uv add` wrote. A binary file
has no patch on GitHub, so its line becomes a `git restore` of the file from the commit. A line that names a renamed file
by its old path gets the command for the new path, which renames the file.

## Where the pages go

| Path in `bla-walk` | Holds |
|---|---|
| `walks/README.md` | A list of every walk, with a link to each of its pages and to its website |
| `walks/ID/read.md` | Read the tutorial, as one page for GitHub |
| `walks/ID/build.md` | Build it yourself, as one page for GitHub. A narrative has none |
| `site/` | The website of the first walk |
| `sites/ID/` | The website of each other walk |
| `.github/workflows/pages.yml` | The workflow that builds the websites with smalldocs, and publishes them on GitHub Pages |

GitHub Pages publishes the first walk at `https://OWNER.github.io/bla-walk/`, and each other walk at
`https://OWNER.github.io/bla-walk/ID/`. An owner with a custom domain gets that domain in place of `OWNER.github.io`.
Do not edit a page by hand, because the next `just walk-update` makes it
again. Edit the notes in the class folder.

The pages need `toc.toml`. A class with only `notes.md` gets no pages. To get them, give the class a `toc.toml` with
one walk.
