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
- **A tutorial takes every tag of its glob.** It cannot pick some steps. For a tutorial on one part of the
  history, give that part tags of its own on a branch, for example `hooks-00` to `hooks-02`.

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

In both modes, the moves of a step go in order. A move has no `just setup` of its own: it builds on what
the moves before it did. So the only way back is the step's **Start**, or **Restart step** in the notes,
and then `just setup`. Whole steps can be visited in any order, because each tag is complete, and its
`just setup` makes all that the step needs.

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
| `steps` | A narrative on some steps, by name, for example `["step-01", "step-03"]` |
| `tags` | A glob for tags of its own, for example `"hooks-*"`. Give `steps` or `tags`, not both |
| `moves` | In a tutorial: `"do"` or `"watch"`, the mode it starts in |
| `sync` | In a tutorial: `false` keeps the slides and the moves apart. Default: `true` |

To add walks to a class:

1. Write `toc.toml`. `class_init.py --toc` writes it for a new class, with the first walk and a tutorial
   to fill in. For a class that exists, copy `templates/class/toc.toml`, and put the project's name in
   place of `@project@`.
2. Make a folder `walks/ID/` for each walk after the first, with its `notes.md`. Add its
   `slides/slides.toml` only when the manifest gives every step a slide.
   For a tutorial, run `just draft ID --write`. It makes the walk's `notes.md` if the folder has none, with a
   section `## step-NN Title` for each step, the title from the tag's message, and a draft section for each
   move. Then write each section by hand.
3. Run `just check`.

With `toc.toml`, `just present ID` opens the walk with that id, and `just present` the first one. `just pdf ID`,
`just check-pdf ID` and `just draft ID` take an id too. `just walk-update` copies `toc.toml`, and the notes
and slides of every walk, into the walk repository. A walk whose folder has nothing yet gets the folder there
with an empty `.gitkeep`, because timewalk does not start when a folder of `toc.toml` is missing. When a walk
leaves `toc.toml`, `just walk-update` lists its files in the walk repository, for you to delete.

Every path of `toc.toml` is from its folder, inside the class folder, with no `..`. `just walk-update` refuses
another, and a path that would take the place of a file of the walk repository: `README.md`, `justfile`,
`AGENTS.md`, `CLAUDE.md`, `.gitignore`, `toc.toml`, `repo/`, `worktree/` or `build/`. When a class goes back to
one walk, `just walk-update` removes `toc.toml` from the walk repository, and lists the files of the walks.
`toc.toml` goes to students as it is, so `just walk-update` refuses a value in it with a private line, such as a
`description` that starts with `> Say:`.

A manifest that misses a step is an error in `just check`. With `toc.toml`, timewalk then does not start.
So give a walk `slides` only once its manifest has an entry for every step. Without a manifest, the check
only warns.

See https://rahuldave.com/timewalk/walks.html#the-table-of-contents and
https://rahuldave.com/timewalk/build-walks.html.

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

### The notes of a tutorial

The text of a step before its first move is about the whole step. The page shows it as "Before the
moves". Put `$ just setup` there, and say what the moves do together.

Then give each move a section `### step-NN.k Title`, in the order of the commits:

- **The instructions** to make the move by hand, with the code to type.
- **The files changed, as a list of their own.** Never name the changed files inside a sentence of prose:
  it is hard to follow. Start the list with "These are the files changed:", or "This is the file
  changed:" for one file. Give each file an item of its own: its path as it is, in code, then what
  happened to it, in words. `timewalk-notes` drafts the list this way. Put what matters in a sentence
  after the list:

  ```markdown
  These are the files changed:

  - `src/tally/__init__.py`: 5 lines added; adds `top`.
  - `tests/test_top.py`: a new file of 8 lines; adds `class Top` and `test_most_common_first`.

  `top` sorts by count, most common first, then by the word.
  ```
- **A line `files:`, with items.** An item is ``- diff `path`: words`` for the change of the move to a
  file, or ``- file `path`: words`` for the file itself. The words say what to look for.
- **A `show:` line under an item,** for example ``show: `for word in text.lower().split():` ``. It quotes
  the main line of the change. The page draws an excerpt of the real diff there, so no diff is copied
  into the notes.
- **The command that shows what the move did, at the end.** It is the anchor of the move. Make it safe
  to run again, and say what it gives. A test that fails is a good anchor, if the notes say so.

Write for both modes. In do mode, the learner makes the move from the notes alone. In watch mode, the
code jumps, so the notes must say what happened.

See https://rahuldave.com/timewalk/notes.html and https://rahuldave.com/timewalk/authoring.html.

### The slides

- **Give every step an entry in the manifest,** even of one slide. A move can have slides of its own.
  Quote its key, for example `"step-02.1" = ["moves.md#1"]`.
- **Leave the background of an SVG picture transparent.** The dark theme inverts the colours of every SVG.
- **Keep every slide file in a slides folder of a walk.** A manifest can name the slides of another walk,
  with a path from its own folder, for example `../../../slides/talk.md#3`.
- **Keep the manifest in a folder of its own, such as `slides/`.** `just walk-update` copies the folder of each
  manifest whole. It refuses a manifest in the class folder itself, or in a folder that holds notes, because
  the notes there have the private lines. It also refuses a slide with a private line, such as `> Say:`, a
  symbolic link, and a PDF that is not the file of an entry of the manifest.

## Check a class

Run these in the class folder, in this order:

1. **`just check`** runs `timewalk-check`. It checks the notes and the slides of every walk against the
   steps. In a tutorial, it also checks the move sections, and each item and `show:` line against the
   change of its move. An error stops `just present` too. Read every warning.
2. **`just draft ID`** runs `timewalk-notes` on a tutorial. It prints a draft section for each move that
   the notes do not have. `just draft ID --write` adds them to the notes. Finish each draft by hand: the
   instructions, the words of each item, the `show:` lines and the anchor. Then run `just check` again.
3. **Run every command of the notes at its commit:** a narrative's at its tag, a tutorial's before its
   first move at the tag before the step, and a move's at the commit of the move. Compare each exit code
   with what the notes say. The method is in
   https://rahuldave.com/timewalk/authoring.html#run-the-commands-of-a-walk.
4. **`just present`,** and open two windows: yours, and the **Room** window that its button opens. Go
   through every walk, step and move, in do mode and in watch mode.
