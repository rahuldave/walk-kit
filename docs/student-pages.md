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
move. It runs `git add -A`, so a new file counts too, and prints nothing when the student's files match.

A student who runs `uv add` a month later gets newer packages, and the files no longer match. So a walk can name
such files in its `loose` list in `toc.toml`, and `git check` then compares them less strictly:

- `pyproject.toml` is compared by the names of its packages. A git text conversion cuts the version off each
  requirement first.
- `uv.lock` is left out of the comparison. `git check` shows a `uv.lock` that only one side has, and runs
  `uv lock --check` on the student's own.
- Any other file that `loose` names has to be there when the commit has it.

## When a student is stuck

Each move has a command under "If you are stuck" that takes the files of the move. It puts the files of the commit
before the move in git's index first, so it deletes only what the move deletes. The student's other files stay.

A walk can skip changes between two parts. The part after such a gap starts with the same kind of command. It puts
the files that the part starts from in place of the student's files.

On the website, each part has a page, and a student can start at any of them. The page gives a command that puts
the files where the part starts into the student's clone. A file that the project deleted before the part stays,
and the page says to delete it if `git check` lists it.

In the notes, a line `patch$ PATH` says that a move changes `PATH` by a patch. In Build it yourself, the line
becomes a command that applies the patch from GitHub, with `curl` and `git apply`. A binary file
has no patch on GitHub, so its line becomes a `git restore` of the file from the commit.

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
`https://OWNER.github.io/bla-walk/ID/`. Do not edit a page by hand, because the next `just walk-update` makes it
again. Edit the notes in the class folder.

The pages need `toc.toml`. A class with only `notes.md` gets no pages. To get them, give the class a `toc.toml` with
one walk.
