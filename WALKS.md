# Walks and tutorials

Read this file before you write the notes of a walk, and before you add a walk to a class. It sums up what
timewalk asks of a class, and the lessons of building one. timewalk's site has the detail, at
https://rahuldave.com/timewalk/. The class timewalk-test, at https://github.com/rahuldave/timewalk-test, is a
worked example of every point here.

## Narratives and tutorials

A walk is one path through the history of the project, with its own notes and slides. A walk is one of
two kinds:

- **A narrative** goes from tag to tag. Each annotated tag marks a step. The message of the tag is the
  note that the class sees.
- **A tutorial** also stops at each small commit between two tags. Each small commit is a move. The class
  makes a step one move at a time.

A tutorial has one or more steps, and each step has zero or more moves. The moves of a step are the
commits after the tag before it, up to its own tag, on the first-parent line. The first-parent line is the
line that git follows back through the first parent of each merge. So keep the history on a straight line.

```
step-01: count the words              tag step-01
step-02.1: a test of counting         move step-02.1
step-02.2: a test of an empty text    move step-02.2
step-02: the tests pass               tag step-02, move step-02.3
```

- **Start the subject of each move with its name and a colon,** `step-NN.k:`. A wrong name is an error.
- **Keep the subject `step-NN:` on the last commit of the step.** It carries the tag, and it is the last move.
- **The first step has no moves.** Give moves to the first steps after it, so that the class meets moves
  early. Keep at least one later step of one commit, with no moves.
- **A tutorial takes every tag of its glob.** It cannot take `steps`. To take a part of a tutorial, write
  a small walk with `select`. See [Small walks out of a big one](#small-walks-out-of-a-big-one). A part with
  a history of its own gets tags of its own on a branch, for example `hooks-00` to `hooks-02`.

See https://rahuldave.com/timewalk/walks.html#tutorial-walks.

## Do mode and watch mode

A tutorial has two modes. The switch **Do** or **Watch** in the step bar changes the mode, at any time, in
every window. The key `moves` in `toc.toml` sets the mode that the walk starts in.

- **Do mode,** `moves = "do"`, the default. The learner makes each move by hand from its notes, and runs
  the command at the end of its section. **Done** marks the move made, or the page marks it when the
  learner's files match the commit of the move. **Catch me up** sets the code to the end of the move.
  **Apply** types a git command into the shell, which makes the change of the move as edits.
- **Watch mode,** `moves = "watch"`. **Show** checks out the commit of each move. The learner reads the
  change, and runs the command at the end of its section.

In both modes, the moves of a step go in order. A move has no `just setup` of its own. It builds on what
the moves before it did. So the only way back is the step's **Start**, or **Restart step** in the notes,
and then `just setup`. The class can visit whole steps in any order, because each tag is complete. The
`just setup` of a step makes all that the step needs.

The notes hold a block for each mode, with the words that differ between the modes. See
[Write for both modes](#write-for-both-modes).

## What timewalk does to git

timewalk never moves the project repository, and never writes to it. It steps in the replay copy, a clone
of the project named `<repo>-replay`, beside it, on the branch `timewalk/replay`. In a walk repository, the
replay copy is `worktree/`, a clone of `repo/`.

- **A move keeps the learner's work, and never asks.** Before a move, timewalk puts the learner's commits,
  staged changes and edits on a branch `timewalk/saved/<place>` in the replay copy, for example
  `timewalk/saved/step-02.1`. The page names the branch, and gives the command that brings a file back.
- **Untracked files stay.** A `.venv`, the outputs of a run and other artifacts stay through every move. A
  file that a later step tracks goes on the saved branch first.
- **`--discard-edits` is not needed,** and the recipes do not pass it.
- **`--in-place` moves the project itself.** Then a move with edits asks, and stashes them.

See https://rahuldave.com/timewalk/git.html for every git consequence, and the pages
https://rahuldave.com/timewalk/replay.html and https://rahuldave.com/timewalk/edits.html.

## The table of contents

A class with one walk keeps `notes.md` and `slides/`, as `class_init.py` makes them. A class with several
walks also has `toc.toml`, with one `[[walk]]` table for each walk. The first walk is the default.

```
bla-class/
├── toc.toml
├── notes.md                  the first walk
├── slides/slides.toml        its slides, and the slide files
└── walks/
    └── tutorial/
        ├── notes.md
        └── slides/slides.toml
```

| Key | Holds |
|---|---|
| `id` | The name of the walk: letters, digits, `-` and `_` |
| `title` | What the menu shows |
| `description` | A sentence or two. The page shows it at the first step of the walk |
| `kind` | `"narrative"`, the default, or `"tutorial"` |
| `notes`, `slides` | The notes file and the manifest of the walk |
| `folder` | In place of `notes` and `slides`: a folder with `notes.md` and `slides/slides.toml` |
| `steps` | A narrative on some steps, by name, for example `["step-01", "step-03"]`. A tutorial takes `select` instead |
| `select` | A small walk: the steps, moves and ranges of moves that it takes out of a bigger walk, for example `["step-04", "step-05.3..step-05.6"]`. Give `steps` or `select`, not both. See [Small walks out of a big one](#small-walks-out-of-a-big-one) |
| `intro` | A Markdown file. The copies of the walk put it before the first step. See [The intro of a walk](#the-intro-of-a-walk) |
| `tags` | A glob for tags of its own, for example `"hooks-*"`. Give `steps` or `tags`, not both |
| `setup` | `"manual"`, the only value: the learner runs `just setup` at each step |
| `moves` | In a tutorial: `"do"` or `"watch"`, the mode it starts in |
| `sync` | In a tutorial: `false` keeps the slides and the moves apart. Default: `true` |

To add walks to a class:

1. Write `toc.toml`. `class_init.py --toc` writes it for a new class, with the first walk and a tutorial
   to fill in. For a class that exists, copy `templates/class/toc.toml`, and put the project's name in
   place of `@project@`.
2. Make a folder `walks/ID/` for each walk after the first, with its `notes.md`. Add its
   `slides/slides.toml` only when the manifest gives every step a slide.
   For a tutorial, run `just draft ID --write`. If the folder has no `notes.md`, it makes one. The file has a
   section `## step-NN Title` for each step, with the title from the tag's message, and a draft section for
   each move. Then write each section by hand.
3. Run `just check`.

With `toc.toml`, `just present ID` opens the walk with that id, and `just present` the first one. `just pdf ID`,
`just check-pdf ID` and `just draft ID` take an id too. `just walk-update` copies `toc.toml`, and the notes
and slides of every walk, into the walk repository. A walk whose folder has nothing yet gets the folder there,
with an empty `.gitkeep`. The folder must be there, because timewalk does not start when a folder of `toc.toml`
is missing. When a walk
leaves `toc.toml`, `just walk-update` lists its files in the walk repository, for you to delete.

Every path of `toc.toml` is from its folder, inside the class folder, with no `..`. `just walk-update` refuses
another path. It also refuses a path that would take the place of a file of the walk repository. These files are
`README.md`, `justfile`, `AGENTS.md`, `CLAUDE.md`, `.gitignore`, `toc.toml`, `repo/`, `worktree/` and `build/`.

When a class goes back to one walk, `just walk-update` removes `toc.toml` from the walk repository, and lists the
files of the walks. `toc.toml` goes to students as it is. So `just walk-update` refuses a value in it with a private
line, such as a `description` that starts with `> Say:`.

A manifest that misses a step is an error in `just check`. With `toc.toml`, timewalk then does not start.
So give a walk `slides` only once its manifest has an entry for every step. Without a manifest, the check
only warns.

See https://rahuldave.com/timewalk/walks.html#the-table-of-contents and
https://rahuldave.com/timewalk/build-walks.html.

## Small walks out of a big one

A small walk takes some steps and moves out of a big tutorial, with the key `select`. It names the notes
and the manifest of the big tutorial, so you write each section once. The walk `small` of timewalk-test:

```toml
[[walk]]
id = "small"
title = "Two parts of tally, one move at a time"
description = "A small tutorial taken out of the big one: two moves of step-02, and one move of step-05."
kind = "tutorial"
notes = "walks/tutorial/notes.md"               # the notes of the whole tutorial
slides = "walks/tutorial/slides/slides.toml"    # its slides
select = ["step-02.2..step-02.3", "step-05.1"]  # a range of moves, and one move
```

`select` takes these entries:

| Entry | Example | The walk takes |
|---|---|---|
| A step | `"step-04"` | The whole step. In a tutorial, the step keeps all its moves |
| A move | `"step-10.3"` | One move, as a small step of its own |
| A range of moves | `"step-05.3..step-05.6"` | The moves from the first to the last, as one small step. Both moves are in one step |

A small step is a step of a walk that holds only some of the moves of a step of the history. It starts at
the commit before its first move. These rules apply, and `just check` reports an error for each one that a
walk breaks:

- **Name the entries in the order of the history,** and take each part once.
- **Keep a range in one step,** from an earlier move to a later one.
- **A narrative takes steps and single moves,** and no range. Its whole step is its tag, and the tag comes
  after the moves of the step. So a move goes before its step, as in `["step-01.2", "step-01"]`.
- **Give `steps` or `select`, not both.**

### The notes of a small walk

A small step shows the commands at the top of the section of its step, then the sections of its moves.
It leaves out the text of the step before its first move. So write the notes of a tutorial in this way,
and a small walk can take any of its moves:

- **Put `$ just setup` at the top of each step's section,** before its first words. Put there every
  command that a move needs before it starts.
- **Write each move section to read alone.** Do not write "as we said above", or "the file from the last
  move". Write each path in full, and give every command of the move, with its anchors, in its section.

`just draft ID --write` for a small walk drafts only the sections that it takes. It writes them into the
notes of the whole tutorial. A small step has no **Edit** button on the page, so edit the notes of the
whole tutorial.

### The intro of a walk

The key `intro` names a Markdown file, which the copies of the walk put before the first step. See
[Copies to read without timewalk](#copies-to-read-without-timewalk). The file must be in the class
folder. `just walk-update` copies it into the walk repository without the private lines, and `just style`
checks it. timewalk does not start when the file of `intro` is missing.

See https://rahuldave.com/timewalk/walks.html#take-a-small-walk-out-of-a-big-one and
https://rahuldave.com/timewalk/authoring.html#write-a-move-to-read-alone.

## Before you write the notes

These rules come from building timewalk-test. They hold for every walk.

### The project

- **The project is a uv project from its first commit,** with `pyproject.toml`, `.python-version` and
  `uv.lock`.
- **Every command in the notes runs through `uv run` or a `just` recipe.** Never write a bare `python`,
  which picks the Python of the system.
- **The project's justfile has a recipe `setup`.** Each step's notes start with `$ just setup`. It makes
  the environment, with `uv sync`, and the artifacts of the step. A second run changes nothing.
- **`just setup` never touches git.** It makes no commit, branch or tag, and changes no config or hook.
  Anything that changes git, for example a hook through `git config core.hooksPath`, is a recipe of its
  own, and the notes ask for it.
- **An artifact is a file that a step needs and that git does not hold,** for example data that a script
  makes, or a report. Git ignores it. `just setup` makes it when it is missing. It stays through every
  move, and a learner who jumps to a later step gets it from that step's `just setup`.

### The history

- **One commit and one annotated tag for each step,** or in a tutorial one commit for each move.
- **Give each tag a short title, a blank line, and a sentence or two.** The page shows the title in bold.
- **A build script makes a history that you can rebuild.** timewalk-test's `history/build.py` writes each
  commit with a fixed author and date, so every build gives the same hashes. It is a good way to keep a
  demo history, and to fix an early step.
- **A step of one commit can be split into moves.** See
  https://rahuldave.com/timewalk/build-walks.html#split-a-step-that-is-one-commit.

### How small to make a move

- **Make each move one atomic action.** An atomic action is one change that makes sense alone, for example
  one test or one new function. The learner types it from the notes.
- **Make each move work alone.** After each move, its anchor commands give the result that the notes state.
- **Give an important command that needs timewalk's own check a move of its own.** timewalk compares the
  learner's files with the commit of a move once for each move. **Your files match** and **Apply** work on
  the whole move.
- **Let two or three less important commands share a move.** A shared command after their block checks
  them. See [How large to make a block](#how-large-to-make-a-block).

See https://rahuldave.com/timewalk/authoring.html#keep-each-move-small and
https://rahuldave.com/timewalk/authoring.html#checks-by-timewalk-come-once-for-each-move.

### The notes of a tutorial

The text of a step before its first move is about the whole step. The page shows it as "Before the
moves". Put `$ just setup` there, and say what the moves do together.

Then give each move a section `### step-NN.k Title`, in the order of the commits:

- **What we do now,** in shared text at the top. Then the code to type in a `do` block, and what to look at
  in a `watch` block. See [Write for both modes](#write-for-both-modes).
- **The files changed, as a list of their own.** Never name the changed files inside a sentence of prose,
  because a reader cannot follow it. Start the list with "The move changes these files:", or "The move
  changes one file:" for one file. A step of a narrative says "The step changes these files:", or "The step
  changes one file:". Give each file an item of its own. The item gives the path as it is, in code, and then
  what happened to the file, in words. `timewalk-notes` drafts the list this way. Then say in a sentence
  after the list which change to read first:

  ```markdown
  The move changes these files:

  - `src/tally/__init__.py`: 5 lines added; adds `top`.
  - `tests/test_top.py`: a new file of 8 lines; adds `class Top` and `test_most_common_first`.

  Read `top` in `src/tally/__init__.py` first. It sorts by count, most common first, then by the word.
  ```
- **A line `files:`, with items.** An item `diff` shows the change of the move to a file. An item `file`
  shows the file itself. The words of the item say what to look for.
- **A `show:` line under an item.** It quotes the main line of the change. The page draws an excerpt of the
  real diff there, so nobody copies a diff into the notes:

  ```markdown
  files:
  - diff `src/tally/__init__.py`: the loop that counts
    show: `for word in text.lower().split():`
  - file `tests/test_top.py`: the whole test
  ```
- **The command that shows what the move did, at the end.** It is the anchor of the move. Make it safe
  to run again, and say what it gives. A test that fails is a good anchor, if the notes say so.

See https://rahuldave.com/timewalk/notes.html and https://rahuldave.com/timewalk/authoring.html.

### Write for both modes

In do mode, the learner makes the move from the notes alone. In watch mode, the code jumps, so the notes
must say what happened. A block for one mode holds the words that differ. A line `::: do` or `::: watch`
opens the block, and a line `:::` closes it.

The page shows a block only in its mode. It shows the text outside the blocks, the shared text, in both
modes. A narrative has no mode, and shows the `watch` blocks.

- **Start with shared text that says what we do now,** for example "Now we teach `main` an option,
  `--top N`."
- **Keep as much as you can in the shared text,** as long as it reads well in both modes. The shared text
  holds the list of changed files, and the line `files:` with its items and `show:` lines. It also holds
  the explanation of the change, and the commands that check it.
- **Put in a block only what differs.** A `do` block holds the commands and the edits that make the move.
  A `watch` block says what to look at, for example a file or a line of the diff.
- **Keep the anchor commands in the shared text.** With an anchor in a `do` block, the move has no
  command in watch mode, and `just check` warns.
- **Close each block, and put no heading and no other block in it.** `just check` reports an error
  otherwise.

```markdown
### step-02.2 A test of an empty text

Now we test an empty text, in a new file, `tests/test_empty.py`. An empty text has no words.

::: do
Make `tests/test_empty.py` with the test `test_empty`.
:::

::: watch
Read the test in the diff below.
:::

The move changes one file:

- `tests/test_empty.py`: a new file of 8 lines; adds `class Empty` and `test_empty`.

files:
- diff `tests/test_empty.py`: an empty text counts nothing.
  show: `self.assertEqual(count(""), {})`

$ uv run python -m unittest discover -s tests -q
```

`just draft ID --blocks --write` drafts a `do` block and a `watch` block in each new move. The tutorial of
timewalk-test, `walks/tutorial/notes.md`, has blocks in every move.

See https://rahuldave.com/timewalk/authoring.html#write-for-both-modes and
https://rahuldave.com/timewalk/walks.html#do-mode-and-watch-mode.

### How large to make a block

A move section can hold several blocks, with shared text between them. Let the importance of a command set
the size of its block:

- **Give an important command a `do` block of its own.** An important command needs a paragraph or more to
  explain. Put the explanation in the shared text before the block. After the block, put a shared command
  that checks the result.
- **Put two or three less important commands in one `do` block.** Give them one line of plan in the shared
  text before the block, and a shared check after it.
- **Give a `do` block a `watch` block beside it when there is something to look at.** A `do` block with
  nothing to look at, such as `mkdir` and a first run of the tests, needs no `watch` block.

A move of one edit has one `do` block for the whole move. A move with several commands has neither a block
for each command, nor one block for all of them. A shared check after a block checks only what its command
shows, and the page shows it apart from the block's commands. Only the shared commands at the end of the
move are its anchor.

timewalk's own check, **Your files match**, comes once for each
move. So plan the moves with the blocks. See [How small to make a move](#how-small-to-make-a-move).

See https://rahuldave.com/timewalk/authoring.html#how-large-to-make-a-block.

### The slides

- **Give every step an entry in the manifest,** even of one slide. A move can have slides of its own.
  Quote its key, for example `"step-02.1" = ["moves.md#1"]`.
- **Leave the background of an SVG picture transparent.** The dark theme inverts the colours of every SVG.
- **Keep every slide file in a slides folder of a walk.** A manifest can name the slides of another walk,
  with a path from its own folder, for example `../../../slides/talk.md#3`.
- **Keep the manifest in a folder of its own, such as `slides/`.** `just walk-update` copies the folder of each
  manifest whole. It refuses a manifest in the class folder itself, or in a folder that holds notes, because
  the notes there have the private lines. It also refuses a slide with a private line, such as `> Say:`. It
  refuses a symbolic link, and a PDF that is not the file of an entry of the manifest.

## Check a class

Run these in the class folder, in this order:

1. **`just check`** runs `timewalk-check`. It checks the notes and the slides of every walk against the
   steps. In a tutorial, it also checks the move sections, and each item and `show:` line against the
   change of its move. It checks each mode as its reader sees it, and warns of a move with no command in
   one mode. An error stops `just present` too. Read every warning.
2. **`just draft ID`** runs `timewalk-notes` on a tutorial. It prints a draft section for each move that
   the notes do not have. `just draft ID --write` adds them to the notes, and `--blocks` adds a `do` and a
   `watch` block to each draft. Finish each draft by hand.
   Write the instructions, the words of each item, the `show:` lines and the anchor. Then run `just check`
   again.
3. **Run every command of the notes at its commit.**
   - Run a command of a narrative at its tag.
   - Run a command of a tutorial before its first move at the tag before the step.
   - Run a command of a move at the commit of the move.

   Compare each exit code with what the notes say. The method is in
   https://rahuldave.com/timewalk/authoring.html#run-the-commands-of-a-walk.
4. **`just present`,** and open two windows. One is yours, and one is the **Room** window that its button
   opens. Go through every walk, step and move, in do mode and in watch mode.
5. **`just style`** checks the prose of the class against the writing guide. Fix every hard problem.

## Copies to read without timewalk

`timewalk-export` writes copies of a walk that a reader can read without timewalk, for example on GitHub
or on a website:

- **`--markdown DIR`** writes `TUTORIAL-do.md` and `TUTORIAL-watch.md` for a tutorial, and `TUTORIAL.md`
  for a narrative.
- **`--site DIR`** writes a website for smalldocs, with a **Do** and a **Watch** section for a tutorial.
  `smalldocs render DIR` builds it. With `--quarto`, the website is for Quarto.

Each copy of a tutorial holds the shared text and the blocks of one mode. The copies leave out the private
lines, and link each step, move and item to the project on GitHub. After each `files:` list, a copy
shows the change of each `diff` item as a `diff` code block. `--intro FILE` puts a file of your own
first, under the title, and `--no-opening` leaves out the text of the notes before the first step.
`timewalk-export` writes over only the files that it made. It refuses a folder inside the project or its
replay copy.

The class has no recipe for the copies yet, and `just walk-update` does not make them. It copies the notes
and the slides for timewalk, and leaves out the private lines by its own rules. So run
`timewalk-export` by hand into `build/` of the class folder, which git ignores. Take timewalk from the
source that `scripts/common.py` names, as the recipes do. Put that source in place of `SOURCE`:

```
uvx --refresh-package timewalk --from SOURCE timewalk-export ../bla --toc toc.toml --walk tutorial --markdown build/copies
```

Do not copy the files into the walk repository by hand. The scan of `just walk-update` for private lines
is the check of what reaches students, and it checks only the commits that it makes. Read every copy
before you publish it.

See https://rahuldave.com/timewalk/walks.html#copies-of-a-tutorial-for-github-and-a-website.
