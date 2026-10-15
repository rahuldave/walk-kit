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

- **Make each move as small as it can be.** A move does one thing, a patch or one `do$` line. A file that a
  command changes after a patch, as `chmod +x` does to a new hook, gets a move of its own.
- **A move needs no name in its subject.** timewalk names it by its place between the tags, and its title
  comes from its `###` heading. So `jj new` is enough to start the next move. A subject such as
  `step-02.1: a test` still helps you read `git log`.
- **The last commit of the step carries the tag.** It is the last move.
- **The first step has no moves.** Give moves to the first steps after it, so that the class meets moves
  early. Keep at least one later step of one commit, with no moves.
- **A tutorial takes every tag of its glob.** It cannot take `steps`. To take a part of a tutorial, write
  a small walk. See [Small walks out of a big one](#small-walks-out-of-a-big-one). A part with
  a history of its own gets tags of its own on a branch, for example `hooks-00` to `hooks-02`.

See https://rahuldave.com/timewalk/walks.html#tutorial-walks.

## Do mode and watch mode

A tutorial has two modes. The switch **Do** or **Watch** in the step bar changes the mode, at any time, in
every window. The key `moves` in `toc.toml` sets the mode that the walk starts in.

- **Do mode,** `moves = "do"`, the default. The learner makes each move by hand from its notes, and runs
  the command at the end of its section. **Done** marks the move made, or the page marks it when the
  learner's files match the commit of the move. **Catch me up** sets the code to the end of the move.
  A `patch$` line gives a button, **Apply patch**, that types `git apply` of the move's patch into the shell.
- **Watch mode,** `moves = "watch"`. **Show** checks out the commit of each move. The learner reads the
  change, and runs the command at the end of its section.

In both modes, the moves of a step go in order. A move has no `just setup` of its own. It builds on what
the moves before it did. So the only way back is the step's **Start**, or **Restart step** in the notes,
and then `just setup`. The class can visit whole steps in any order, because each tag is complete. The
`just setup` of a step makes all that the step needs.

The notes hold a block for each mode, with the words that differ between the modes. See
[Write for both modes](#write-for-both-modes). The pages that students read keep the two modes as two ways of
reading. **Build it yourself** is do mode, and **Read the tutorial** is watch mode. See
[The pages that students read](#the-pages-that-students-read).

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
| `select` | A small walk: the steps, moves and ranges of moves that it takes out of a bigger walk, for example `["step-04", "step-05.3..step-05.6"]`. An entry can have a title. Give `steps` or `select`, not both. See [Small walks out of a big one](#small-walks-out-of-a-big-one) |
| `intro` | A Markdown file about the walk. The page shows it at the first stop, and the pages that students read put it before the first part. See [The intro of a walk](#the-intro-of-a-walk) |
| `shared` | A small tutorial with notes of its own: the notes of the big tutorial, where its include lines take the sections of its moves. Not with `select`, `steps` or `intro`. See [A small walk with notes of its own](#a-small-walk-with-notes-of-its-own) |
| `loose` | In a tutorial: the files that do mode compares by the names of their packages, for example `["pyproject.toml", "uv.lock"]`. See [Files made with uv add](#files-made-with-uv-add) |
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
   each move. Then write each section by hand. See
   [Write for a reader who has never heard of timewalk](#write-for-a-reader-who-has-never-heard-of-timewalk).
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

An entry in braces gives its stop a title, for example
`select = [{ range = "step-05.3..step-05.6", title = "Types" }, "step-06"]`.

`select` takes these entries:

| Entry | Example | The walk takes |
|---|---|---|
| A step | `"step-04"` | The whole step. In a tutorial, the step keeps all its moves |
| A move | `"step-10.3"` | One move, as a small step of its own |
| A range of moves | `"step-05.3..step-05.6"` | The moves from the first to the last, as one small step. Both moves are in one step |
| An entry with a title | `{ range = "step-05.3..step-05.6", title = "Types" }` | What `range` names, a step, a move or a range of moves, with a title |

A small step is a step of a walk that holds only some of the moves of a step of the history. It starts at
the commit before its first move. These rules apply, and `just check` reports an error for each one that a
walk breaks:

- **Name the entries in the order of the history,** and take each part once.
- **Keep a range in one step,** from an earlier move to a later one.
- **A narrative takes steps and single moves,** and no range. Its whole step is its tag, and the tag comes
  after the moves of the step. So a move goes before its step, as in `["step-01.2", "step-01"]`.
- **Give `steps` or `select`, not both.**

**Give each range a title.** A range without one has no title in the pages that students read and the PDF. The title shows
in the step bar, the notes, the browser tab, the PDF and the pages. A title for a step or a move takes
the place of its title in the notes. See https://rahuldave.com/timewalk/walks.html#a-title-for-a-stop.

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

The key `intro` names a Markdown file about the walk. At the first stop of the walk, the notes column
shows it under "About this walk", in do mode, in watch mode and in a narrative. Its cues hide in the Room
window. The pages that students read put it before the first part. See
[The pages that students read](#the-pages-that-students-read).

The intro of every tutorial explains once what a move is. A move is one small change, made by one patch or one
command. The learner makes each move, and the page checks the learner's files against it. After the intro, the
text can use the word "move". See
[Write for a reader who has never heard of timewalk](#write-for-a-reader-who-has-never-heard-of-timewalk).

Give a small walk an intro that says which moves it leaves out between its parts. The file must be in the
class folder. `just walk-update` copies it into the walk repository without the private lines, and `just style`
checks it. timewalk does not start when the file of `intro` is missing.

See https://rahuldave.com/timewalk/walks.html#take-a-small-walk-out-of-a-big-one and
https://rahuldave.com/timewalk/authoring.html#write-a-move-to-read-alone.

### A small walk with notes of its own

A small tutorial can have a notes file of its own in place of `select` and `intro`. Its include lines take
the sections of its moves from the notes of the big tutorial, so each move section is still written once.
Choose it when the walk needs its own words that the big tutorial does not have:

- text at a stop, before its moves, between them or after them
- what the walk skipped since the stop before
- a recap after the moves of a stop

If the sections of the big tutorial are enough, choose `select` and `intro`. They have fewer parts to keep up.

```toml
[[walk]]
id = "testing"
title = "The tests of tally, with notes of its own"
description = "A small tutorial with its own words at each stop: what it leaves out, and what the moves did."
kind = "tutorial"
notes = "walks/testing/notes.md"    # its own notes: an intro, and a ## stop for each place, with its includes
shared = "walks/tutorial/notes.md"  # the notes that its {{include ...}} lines take move sections from
slides = "walks/tutorial/slides/slides.toml"
```

Write its notes in this way:

- **Write the intro before the first `##`.** It takes the place of `intro`. Say there what a move is.
- **Start each stop with `## Title`.** The words are the title of the stop, with no step name.
- **Put in moves with include lines.** Write each on a line of its own, for example `{{include step-02.1}}`,
  `{{include step-02.2..step-02.3}}` or `{{include step-04}}`. The includes of a stop make one
  whole step, or moves of one step with no move left out. For moves after a gap, start a new stop.
- **Write `$ just setup` above the first include of a stop of moves.** A walk with notes of its own does not
  add the commands at the top of the step's section. An include of a whole step brings them.
- **Put no `files:` list, no `do$` line and no `### step-NN.k` heading in the walk's own text.** The moves
  bring them. Prose, cues, `$` lines and blocks `::: do` and `::: watch` are good.
- **Keep each include outside the blocks `::: do` and `::: watch`.** An include brings moves for both modes.
- **Do not run a first command of a step again in a stop that includes the whole step.** The step brings it.
- **Put the stops in the order of the history,** and take each move once.

`just check` reports each mistake, one for each stop, and timewalk does not start after an error. An edit
of the words shows at once. Restart timewalk after you add or remove a stop, or change its includes or its
title. The page has no **Edit** button for such a walk, so edit both files
in your editor. `just draft ID --write` writes the missing move sections into the shared notes.

`just walk-update` copies the walk's own notes whole, with the intro, and the `shared` file, each without
the private lines. The walks `testing` and `finish` of timewalk-test are examples. See https://rahuldave.com/timewalk/walks.html#a-walk-with-notes-of-its-own.

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
  learner's files with the commit of a move once for each move. **Your files match** works on the whole move.
- **A move that runs `uv add` or `uv lock` needs `loose`.** Write the command as a `do$` line. See
  [Files made with uv add](#files-made-with-uv-add).
- **Let two or three less important commands share a move.** A shared command after their block checks
  them. See [How large to make a block](#how-large-to-make-a-block).

See https://rahuldave.com/timewalk/authoring.html#keep-each-move-small and
https://rahuldave.com/timewalk/authoring.html#checks-by-timewalk-come-once-for-each-move.

### Files made with uv add

`uv add` writes the newest version of a package into `pyproject.toml` and `uv.lock`. A learner who makes
the move on a later day gets a newer version, and **Your files match** never comes. So a tutorial with
moves that run `uv add` or `uv lock` writes each such command as a `do$` line in the shared text, for
example `do$ uv add --group test pytest`. See [Write for both modes](#write-for-both-modes). It also sets
this key in its table in `toc.toml`:

```toml
loose = ["pyproject.toml", "uv.lock"]
```

Do mode then compares these files by the names of their packages, and not by their versions. Any other
file that `loose` names is not compared by its contents, but it must be there when the move makes it.
`just check` warns of an entry that no move changes. See
https://rahuldave.com/timewalk/walks.html#files-that-match-by-the-names-of-their-packages.

### Write for a reader who has never heard of timewalk

A learner reads the notes in timewalk, or on the pages that `just walk-update` makes for the walk repository. See
[The pages that students read](#the-pages-that-students-read). The reader knows the program, or wants to learn it.
The reader does not know timewalk, and does not need to. These rules hold for every walk, a narrative too.

- **Keep timewalk's words out of the text.** "step", "commit", "Start", "Before the moves" and a name such as
  `step-02.4` are timewalk's words. Do not write them in the text of the notes. The heading `### step-02.1 Title`
  keeps its name, because timewalk needs it. Only its title is for the reader.
- **Explain a move once, in the intro of every tutorial.** Always write this explanation. The intro is the text
  of the notes before the first step, or the file of `intro`. A move is one small
  change, made by one patch or one command. The learner makes each move, and the page checks the learner's files
  against it. After the intro, the text can use the word "move" anywhere. The intros of `walks/tutorial/notes.md`
  and `walks/hooks/notes.md` in timewalk-test do it.
- **Open a step with what we build, and why,** in terms of the program. For example, write "We cannot tell
  whether `tally` still works after a change, so we write tests." Do not write "The commits of this step add tests."
- **Open a move with the problem, and the change that solves it.** Do not open with "Now we add X". Do not open
  with a list of files, or with a link to a diff.
- **Then give the change, piece by piece.** Each piece says in the shared text what it changes, and why. The
  shared text is the text outside the blocks for one mode. See [Write for both modes](#write-for-both-modes).
  - **Each file of the move comes from one line.** A `do$` line gives a command that writes it. A `patch$` line
    names a file that the move changes by a patch. Do not copy the code into the notes. The code comes from the
    project. See [Where each file comes from](#where-each-file-comes-from).
  - **In do mode,** say what to read in each patch, and where in the file, for example "after the line `X`" or
    "in place of the function `f`".
  - **In watch mode,** say what the change does, and where to see it. "Read the change of `pyproject.toml`."
    alone explains nothing.
- **Then give the check.** Give a command, what it prints, and what that shows.
- **Last, write `files:`,** with an item and its words for every file of the change, `uv.lock` too. Do not write
  a list of the files in prose, such as "The move changes these files:". The pages make that list from the facts
  file.
- **Keep the same rules in the text of a small walk.** Its intro and the text at its stops are for the same
  reader. See [The notes of a small walk](#the-notes-of-a-small-walk).

The diffs are the data that the learner checks against. They help, but they are not the explanation. So the text
above `files:` must explain the change without them. `just check` finds timewalk's words in the text, and each
file of a move that no `do$` line writes and no `patch$` line names. See [Check a class](#check-a-class).

### Where each file comes from

A file of a move gets its content in one of two ways:

- **A command writes it.** For example, `do$ uv add ruff` writes `pyproject.toml` and `uv.lock`.
- **A patch brings it in.** The author changes the file by hand, and a `patch$` line names it. See
  [patch$ lines](#patch-lines).

The notes never copy code for the reader to type. Every diff and every file that a reader sees comes from the
project's history, or from the learner's own files. `timewalk-check` tells the two ways apart. It runs the `do$`
lines of each move at the commit before the move, in a scratch clone of the project. It notes the files that each
line writes, and keeps the result in a cache, so the second check is fast. It warns of these cases:

- A file that no `do$` line writes, and no `patch$` line names. Add `patch$ PATH`.
- A file that a `do$` line writes and the move then changes. Add `patch$ PATH` for that change too.
- A `do$` line that writes a file that the move does not change. The move and its commands disagree.
- A `do$` line that fails at the commit before the move.

The warnings mark a move that does not do one thing. For example, `do$ chmod +x hooks/pre-commit` fails before
the move, when the move also brings in `hooks/pre-commit` by a patch. A file of the walk's `loose` that a `do$` line
writes with newer versions, such as `uv.lock`, counts as the line's.

The facts file says where each file comes from, and Build it yourself shows it. A file of a command says which
command. A patch is open, to make by hand. `timewalk-check --no-run` runs nothing, and checks only the moves
without `do$` lines. A `patch$` line that names a file that the move does not change is an error.

See https://rahuldave.com/timewalk/authoring.html#write-for-a-reader-who-has-never-heard-of-timewalk.

### patch$ lines

A line `patch$ PATH` says that the move changes the file `PATH` by a patch, the diff of the move's commit. Put
it in the section of the move, in the shared text, after the words that explain the change. Write a path with a
space in backticks, for example ``patch$ `my file.py` ``.

```markdown
`just check` works only when someone runs it. A hook runs it every time. The hook, `hooks/pre-commit`, has
three lines. The file comes whole, as a patch.

patch$ hooks/pre-commit
```

- **In timewalk, in do mode,** the line shows **Apply patch**, which types `git apply` of the patch into the
  shell. If the learner has changed the file, it shows **Replace with the move's file** instead. That button
  first keeps the learner's version on a branch `timewalk/saved/<move>-yours`. Neither button merges, so a file
  never gets conflict markers.
- **In timewalk, in watch mode,** the line reads "A patch to PATH", with **See diff**.
- **On the pages,** Read the tutorial shows "A patch to `PATH`.", linked to the file in What changed. Build it
  yourself shows "Apply the patch to `PATH`:", and a command that applies the patch from GitHub. See
  [The pages that students read](#the-pages-that-students-read).
- **The learner can also make the change by hand.** The match marks the move done when the files match.

A file that a `do$` line writes needs no `patch$` line. If the move then changes that file further, it needs a
`patch$` line too. Build it yourself then gives a `git apply` command after the `do$` line, with the rest of the change
in the command. A command on a file that a patch brings in gets a move of its own. In timewalk-test, the move
`hooks-01.2` brings in `hooks/pre-commit` by `patch$ hooks/pre-commit`. The next move, `hooks-01.3`, is
`do$ chmod +x hooks/pre-commit` alone.

`just check` warns of a `patch$` line in a `do` or `watch` block, or above the first move of a step with moves.
A step of one commit has no moves, and its `patch$` lines go in the step's own section. `just check` also warns of a
sentence that asks for **Apply this file** or **Apply the whole move**, which timewalk no longer has.

### The notes of a tutorial

Write the text of a step before its first move section. The text is about the whole step. The notes column shows
it in a section of its own, under the title of the step. Put `$ just setup` there, and say what the step builds,
and why.

Give each move a section `### step-NN.k Title`, in the order of the commits. Each section has these parts, in
this order:

- **The problem, and the change that solves it,** in the shared text, for both modes.
- **The change, piece by piece.** Each file comes from a `do$` line or a `patch$` line, in the shared text. In a
  `do` block, say what to read in each patch, and where in the file. Copy no code. In a `watch` block, say what the
  change does, and where to see it. See [Write for both modes](#write-for-both-modes).
- **One or more anchor commands, in the shared text.** An anchor command is the check of the move. Make it safe
  to run again, and say what it prints and what that shows. A test that fails is a good anchor, if the notes say
  that it fails. The notes column shows the anchor commands under the label "Check it".
- **Last, a line `files:`, with items.** Give an item to every file of the commit, `uv.lock` too. An item `diff`
  shows the change of the move to a file. An item `file` shows the file itself. The words of the item say what
  to look for in the file. On the pages, What changed shows the words of each item beside its file.
- **A `show:` line for the main line of the move.** Under its item, quote that line of the change. The page
  draws an excerpt of the real diff there, so nobody copies a diff into the notes:

  ```markdown
  files:
  - diff `src/tally/__init__.py`: one word, `lower()`, answers the failing test.
    show: `for word in text.lower().split():`
  - file `tests/test_top.py`: the whole test
  ```

  Put a line with a backtick in it in two backticks, for example
  ``` show: ``The command `wikiapp` uses this library.`` ```. `just check` warns of a `show:` line that GitHub
  would show wrong, and says how to write it. See
  https://rahuldave.com/timewalk/walks.html#quote-a-line-with-backticks.

A step of a narrative follows the same order. Its text says what the step builds and why, then the change, the
check, and last `files:` with an item for every file of the step.

`just draft ID` drafts each new move section in this shape, with a comment for each part, and an item under
`files:` for every file of the commit. Replace each comment with the text.

See https://rahuldave.com/timewalk/notes.html and https://rahuldave.com/timewalk/authoring.html.

### Write for both modes

In do mode, the learner makes the move from the notes alone. In watch mode, the code jumps, so the notes must say
what happened. A block for one mode holds the words that differ. A line `::: do` or `::: watch` opens the block,
and a line `:::` closes it.

The page shows a block only in its mode. It shows the text outside the blocks, the shared text, in both modes. A
narrative has no mode, and shows the `watch` blocks.

- **Keep as much as you can in the shared text,** as long as it reads well in both modes. The shared text holds
  these parts:
  - the problem, and the change that solves it, before the blocks
  - the explanation of each piece of the change
  - a `patch$` line for each file that the move changes by a patch
  - each command that makes the move, as a `do$` line
  - the commands that check the result, and what they print
  - last, the line `files:` with its items and `show:` lines
- **Put in a block only what differs.** A `do` block says what to read in each patch, and where in the file. It
  copies no code. A `watch` block says what the change does, and names the file and the
  line to look at.
- **Write a command that makes the move as a `do$` line in the shared text.** Do mode is for the learner to run,
  and watch mode is for the learner to watch. A command makes the move if it changes the files to what the commit
  of the move has. Examples are `uv add`, `uv lock`, `rm`, `ruff check --fix` and `chmod +x`. In do mode, a
  `do$` line is a command to run. In watch mode, the page shows the command, with nothing to run.
- **Keep a check as a shared `$` line,** for example `$ just test`. A `$` line runs in both modes, so it must
  change no tracked file.
- **Keep the anchor commands in the shared text.** With an anchor in a `do` block, the move has no command in
  watch mode, and `just check` warns. A `do$` line is never an anchor. A move whose only commands are `do$` lines
  has no anchor, and `just check` warns of it too.
- **Put no `do$` or `patch$` line in a block.** `just check` warns of it, because these lines show in both modes.
- **Close each block, and put no heading and no other block in it.** `just check` reports an error otherwise.

The example follows every rule. It opens with the problem, gives a `do$` line and a `patch$` line, says what to
read in do mode, and says what to look at in watch mode. Then it gives the check, and last an item for every file, `uv.lock` too. The walk sets
`loose`, because the move runs `uv add`. See [Files made with uv add](#files-made-with-uv-add).

````markdown
### step-02.1 A test of counting

We cannot tell whether `count` still works after a change, unless we try it by hand each time. A test
tries it for us. pytest finds the tests of the project and runs them, so we add it to the project first.

do$ uv add --group test pytest

The command puts pytest in a group `test` of `pyproject.toml`, and its exact version in `uv.lock`. The first
test comes in a file of its own, `tests/test_count.py`, as a patch.

patch$ tests/test_count.py

::: do
Read its one test, `test_counts_each_word`, before you run it.
:::

::: watch
The new file `tests/test_count.py` holds one test, `test_counts_each_word`. It gives `count` the
text `"a b a"`, and expects `a` twice and `b` once.
:::

$ uv run pytest -q

pytest prints `1 passed`. So `count` counts each word of a short text.

files:
- diff `pyproject.toml`: pytest, in the group `test`.
- file `tests/test_count.py`: the first test of `count`.
  show: `assert count("a b a") == {"a": 2, "b": 1}`
- diff `uv.lock`: the exact version of pytest, and of the packages that it needs.
````

The tutorial of timewalk-test, `walks/tutorial/notes.md`, has blocks in every move. The walk `hooks` of
timewalk-test brings in its hook with `patch$ hooks/pre-commit` in one move, and makes it executable with
`do$ chmod +x hooks/pre-commit` in the next, in `walks/hooks/notes.md`.

See https://rahuldave.com/timewalk/authoring.html#write-for-both-modes and
https://rahuldave.com/timewalk/walks.html#do-mode-and-watch-mode.
### How large to make a block

A move section can hold several blocks, with shared text between them. Let the importance of a command set
the size of its block:

- **Give an important command a part of its own.** An important command needs a paragraph or more to
  explain. Put the explanation in the shared text before the command. After it, put a shared command that
  checks the result.
- **Put two or three less important commands together.** Give them one line of plan in the shared text
  before them, and a shared check after them.
- **Give a group of commands a `watch` block beside it when there is something to look at.** A group with
  nothing to look at, such as `mkdir` and a first run of the tests, needs no `watch` block.

A command that makes the move is a `do$` line, and needs no `do` block. A command for do mode alone, such
as `mkdir` before an edit by hand, goes in a `do` block. A move of one edit has one `do` block for the
whole move. A move with several commands has neither a block for each command, nor one block for all of
them. A shared check after a block checks only what its command
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
   one mode. A public cue, such as `> Try:`, in the blockquote of a private cue is an error. An error
   stops `just present` too. Read every warning. Then, in a class with `toc.toml`, it checks the pages that
   students read. See [The checks of the pages](#the-checks-of-the-pages).
2. **`just draft ID`** runs `timewalk-notes` on a tutorial. It prints a draft section for each move that
   the notes do not have, with a `do` and a `watch` block, and an item under `files:` for every file of the
   commit. `just draft ID --write` adds them to the notes. The option `--blocks` is still accepted, and changes
   nothing. Finish each draft by hand, by the rules of
   [Write for a reader who has never heard of timewalk](#write-for-a-reader-who-has-never-heard-of-timewalk).
   Write the problem and the change, where to make each change, what to look at, the anchor, the words of each
   item and the `show:` lines. Then run `just check` again.
3. **Run every command of the notes at its commit.**
   - Run a command of a narrative at its tag.
   - Run a command of a tutorial before its first move at the tag before the step.
   - Run a command of a move at the commit of the move.

   Compare each exit code with what the notes say. The method is in
   https://rahuldave.com/timewalk/authoring.html#run-the-commands-of-a-walk.
4. **`just present`,** and open two windows. One is yours, and one is the **Room** window that its button
   opens. Go through every walk, step and move, in do mode and in watch mode.
5. **`just style`** checks the prose of the class against the writing guide. Fix every hard problem.

## The pages that students read

A student can read each walk without timewalk, on GitHub or on the website of the walk repository.
`just walk-update` makes these pages from the notes. The pages are for a reader who has never heard of timewalk, so
they never name timewalk's steps or commits. They name a move, which the intro of a tutorial explains.

### Two ways of reading

A tutorial has two ways of reading, from the same notes:

- **Read the tutorial** explains each change, with the code to look at. It holds the shared text and the `watch`
  blocks, as watch mode does. A command that made the change shows as a sentence, with nothing to run.
- **Build it yourself** gives every command to run and every patch to apply, so that the student makes the
  project. It holds the shared text and the `do` blocks, as do mode does. Its patches come from the facts
  file, never from code in the notes.

Build it yourself works without timewalk, in the student's own clone of the project. The pages take their
commands from the facts file:

- **Get the project.** `git clone`, then `git switch -c mine START`, where `START` is the commit where the walk
  starts.
- **`git check`.** **Get the project** also sets up a git alias, so that `git check SHA` compares the student's files with
  a commit. It runs `git add -A` in a copy of git's index, `.git/check-index`, so a new file counts too, and the
  student's own index does not change. It prints nothing when the files match. After each move, the page gives
  `git check` with the move's commit. The student never commits, so git's index does not hold the student's work. A `git rm` of a
  file that the walk changed fails with "local modifications", and a `git mv` of a file that the walk made fails with
  "not under version control". Write `rm` and `mv` in the notes in their place. `just check` names each `git rm` of a file that the walk added or changed
  before it, and each `git mv` of a file that the walk added before it. A `git mv` or `git rm` of a file that the walk has not
  changed works. `git check` compares only the files, so
  it needs nothing from git's index.
- **Take the files of a move.** A student who is stuck runs
  `git restore --source BEFORE --staged -- :/ && git restore --source SHA --staged --worktree -- :/`. The first
  half puts the files of the commit before the move in git's index. The second half deletes each file that the
  index has and `SHA` does not, so it deletes only what the move deletes. The student's own files stay.

### git check and loose

timewalk compares the files that a walk's `loose` names by the names of their packages, so that a student who
runs `uv add` a month later still matches. `git check` aims for the same:

- A `pyproject.toml` goes through a git text conversion, `diff.names.textconv`, that cuts the version off each
  requirement before git compares it.
- A `uv.lock` is left out of the comparison, because a newer package can bring new packages with it. `git check`
  shows a `uv.lock` that only one side has, and runs `uv lock --check` on the student's own.
- A move can change `pyproject.toml` and leave `uv lock` to the next move. At that move, the project's own `uv.lock`
  fails `uv lock --check`. The renderer finds such moves: it runs `uv lock --check` on the files of each commit in a
  scratch folder, offline first, and keeps the result in `~/.cache/walk-kit/locks`. At such a move, the page gives
  `git check SHA --stale-lock`, which leaves out `uv lock --check`.
- Any other file that `loose` names has to be there when the commit has it, and not there when the commit does not.

With `loose`, `git check` prints the lines that differ, not a list of files, because the text conversion works
on lines.

### A gap, a page of its own, and a binary file

A small walk can skip commits between two stops. The stop after the gap starts with the same command as
**Take the files of a move**, from the end of the stop before to the start of this one.

On the website, each stop has a page, and a student can start there. The page gives
`git rm -rq --cached --ignore-unmatch -- :/ && git restore --source START --staged --worktree -- :/`, with the
commit where the stop starts as `START`. It empties the index first, so none of the student's files go. A file that
the project deleted before the stop stays too, and the page says to delete it if `git check` lists it.

GitHub's diff has no data for a binary file, so a `patch$` line of a binary file gives
`git restore --source SHA --worktree -- ':(top,literal)PATH'` in place of a patch.

A `patch$` line can name a file that the change renames by its old path. `git apply --include` matches the new path
of a renamed file, so the command names the new path. The patch then deletes the old file and writes the new one.

A narrative has one way of reading, Read the tutorial. The app keeps its own switch, **Do** and **Watch**.

### What changed

Each part of the pages ends with a section **What changed**. The section is the same in every part, so a reader
learns it once:

- every file of the change, with the words of its `files:` item, or else the names of the functions, classes and
  recipes that the change adds, changes or removes. Then come its counts of lines, the `do$` line that writes it,
  and a link to the file as the change left it.
- the whole diff of each file, folded. A lockfile, such as `uv.lock`, and a binary file get no diff. In Build it
  yourself, each patch is open: the whole diff of a file that no `do$` line writes, and the lines that the move
  changes after the `do$` line that writes a file.
- a link to the change on GitHub, and a link to the code after it

In Build it yourself, the diffs under What changed are open, with a summary. A patch reads "The patch to
`PATH`". A file that a `do$` line writes and the move then changes reads "After `CMD`, the patch to `PATH`".

The text above What changed explains the change, and What changed is the data that the reader checks against. Two
forms of the notes become links on the pages:

- A `patch$` line becomes "A patch to `PATH`." in Read the tutorial, with a link to the file in What changed. In
  Build it yourself, it becomes "Apply the patch to `PATH`, from the top of the project:", and a command that
  applies the patch from GitHub, `curl -sL https://github.com/OWNER/NAME/commit/SHA.diff | git apply --include=PATH`.
  For a part of several commits, the address is `OWNER/NAME/compare/BASE...SHA.diff`. A file that a `do$` line
  writes first gets no command, as the whole change would not apply on top of it. Its line says "Then change `PATH`
  as its patch shows", and its patch is open under What changed. See [patch$ lines](#patch-lines).
- "the change of `X`", with `X` a file of the change, becomes a link to the entry of `X` in What changed.

### How the pages are made

`just walk-update` makes the pages in these stages:

1. It runs `timewalk-export --json` for each walk of `toc.toml`. The command writes the facts file, a JSON file with
   the text, the commands, the items and the changed files of every part of the walk, without the private lines.
   A walk that takes the same notes and the same part of the history as a walk before it, in another mode, gets
   no pages of its own.
2. It refuses to go on if `timewalk-check` finds an error in a walk. Run `just check`, and fix the error.
3. It renders every page with the walk skill's `scripts/render.py`, before it writes the first file.
4. It writes the pages into the walk repository, and removes the pages of an earlier run that the walks no longer
   have. It never writes over a file that `render.py` did not make. It refuses such a file, and writes nothing.

The pages need `toc.toml`. A class with only `notes.md` gets no pages, and `just walk-update` says so. To get them,
give the class a `toc.toml` with one walk. See [The table of contents](#the-table-of-contents).

### Where the pages go

| Path in the walk repository | Holds |
|---|---|
| `walks/README.md` | A list of every walk, with a link to each of its pages and to its website |
| `walks/ID/read.md` | Read the tutorial, as one page for GitHub |
| `walks/ID/build.md` | Build it yourself, as one page for GitHub. A narrative has none |
| `site/` | The website of the first walk, for smalldocs: a front page that explains the two ways and links to the website of each other walk, and a page for each part in `read/` and in `build/` |
| `sites/ID/` | The website of each other walk. Its front page links back to the website of the first walk |
| `.github/workflows/pages.yml` | The workflow that builds the websites and publishes them on GitHub Pages |

Do not edit a page by hand. Its first line says that `render.py` made it, and the next `just walk-update` makes it
again. Edit the notes in the class folder. A walk after the first cannot have the id `read`, `build` or
`site_libs`, because the website of the first walk has folders with those names.

### Turn on GitHub Pages

On each push to `main`, the workflow builds `site/` and every folder in `sites/` with smalldocs. GitHub Pages then
publishes the first walk at `https://OWNER.github.io/bla-walk/`, and each other walk at
`https://OWNER.github.io/bla-walk/ID/`. An owner with a custom domain gets that domain in place of `OWNER.github.io`.
The workflow publishes nothing when `site/` is missing. Do these steps once for each walk repository:

1. Open the repository on GitHub, then **Settings**, then **Pages**.
2. Under **Source**, choose **GitHub Actions**.
3. Push `main`. The **Actions** tab shows the run of the workflow, and its address.

`just walk-init` writes the workflow, and `just walk-update` writes it again from the template. A walk repository
that has its own workflow at that path keeps it, because it matches no version of the template. Then
`just walk-update --replace-edited` puts the template in its place. It also makes again every other file that
has an edit by hand, such as the justfile.

### The checks of the pages

`just check` checks the pages after `timewalk-check`, with `render.py --class`. For each walk that gets pages, it
renders the pages in a temporary folder, and writes nothing in the walk repository. It reports two kinds of
problem, and the exit code is 1 if it finds one. It also prints warnings, which do not change the exit code.

| Problem | Example of the report | Fix |
|---|---|---|
| Facts made without running the `do$` lines | `step-03.1: the do$ lines did not run, so Build it yourself cannot say which files they make` | Make the facts without `--no-run`, and without `TIMEWALK_NO_RUN` set |
| A page against the writing guide | `build.md: HARD 8: 31 words (at most 25): ...` | Fix the text of the notes that the page shows, often the words of an item. The page comes from the notes |

The warnings are of one kind:

- **timewalk's words in the text that a reader sees**, for example `warning: step-02.1: "step" in: Now we add a test
  in this step`. Say it in the words of the program. The check reads the text, the words of each item and the
  titles, and skips headings, code, the addresses of links and HTML comments. It finds "step" and "commit" in any
  case, and "Start" inside a sentence. "Start the server" is a verb, and passes. A lesson on git
  can need the word "commit", so this is a warning and not a problem.

Where each file of a move comes from is `timewalk-check`'s to judge. See
[Where each file comes from](#where-each-file-comes-from).

`just walk-update` runs the checks of the pages too, and says how many it finds. It writes the pages all the same.
`just check` lists each problem.

### Make the pages, and follow them

`just pages` writes the pages alone, and commits nothing. With a walk repository, it writes into it, through
`walk_update.py --pages-only`, with the same checks as `just walk-update`, and a later `just walk-update` commits them.
Without one, `render.py --pages build/pages` writes the same layout into the class folder. It then runs only the
checks of `render.py`, and no check for private lines. Run `just walk-update` before the pages go to students.

`just follow` makes the pages, and then follows each Build it yourself page with `scripts/follow.py`. It clones the
project into a scratch folder and runs every command of the page in order. A `curl` of a diff on GitHub becomes the
same `git diff` in the local project. A command that fails is logged, not counted. Only a `git check` that prints
something, or fails, is a failure. The catch-up command after a check, `git restore --source ... --staged ...`, runs
only after that check fails. follow counts the `git check` lines of the page, and fails if it ran another number of
checks, or if the page has none. The log is `build/follow/ID.md`. A class without `toc.toml` has no pages, and
`just follow` says that it has nothing to follow.

With Claude Code installed, follow also makes one call to a model with the page and the log, with the prompt in
`review/output.md`. The model reports each output, number or claim of the text that the log does not show. The
report is `reports/follow/ID-build.md`, and each run writes it again. A finding fails the recipe. Fix the notes, and
run it again.

### A class made before the pages

`just walk-update` writes the files of the walk repository, and never the justfile of the class. So the `check`
recipe of an older class does not check the pages, and the class has no recipes `pages` and `follow`. Copy those
recipes from the template too. To add the checks, copy the last lines of the recipe `check`
from `templates/class/justfile` into the class's `justfile`. These lines start at the comment about the pages
that students read.

A class that made its pages with a script of its own can drop that script. `just walk-update` now makes the pages.
First remove the old pages from the walk repository, and commit, because `just walk-update` never writes over a
page that `render.py` did not make. Its own workflow stays until `just walk-update --replace-edited`.

timewalk can also write its own copies of a walk, with `timewalk-export --markdown DIR` or `--site DIR`. A class
does not need them. See https://rahuldave.com/timewalk/walks.html#copies-of-a-tutorial-for-github-and-a-website.
