---
title: The three repositories
---

Your notes hold cues for you alone, such as what to say and how long a step takes. The project is public, and
students clone it. So anything for teaching that you put in the project goes to every student. walk-kit keeps the teaching material
out of the project, and splits it into a private part and a public part.

| Repository | Holds | Who sees it |
|---|---|---|
| `bla` | The project. One commit and one annotated tag `step-NN` for each step | Public |
| `bla-class` | Your notes with private cues, the slides, `toc.toml` and the recipes | Private |
| `bla-walk` | The notes without private cues, the slides, a justfile, and the pages that students read | Public. Students fork it |

The three folders sit side by side, for example `~/Projects/bla`, `~/Projects/bla-class` and
`~/Projects/bla-walk`. The class justfile finds the other two as `../bla` and `../bla-walk`. So a clone of the class
folder on another machine needs only `just setup`, which clones the other two. To keep them in other folders, set
`PROJECT_DIR` and `WALK_DIR`.

## Edit only the class folder

You edit everything in `bla-class`, and never in `bla-walk`. `just walk-update` makes `bla-walk` from the class
folder. It shows the diff, and asks before it commits. It never pushes.

| What | Where in `bla-class` |
|---|---|
| The notes of each step | `notes.md`, one section for each step, `## step-NN Title` |
| The slides | `slides/*.md`, and the pictures beside them |
| Which slides show at which step | `slides/slides.toml` |
| The list of walks | `toc.toml` |
| Each walk after the first | `walks/ID/notes.md` and `walks/ID/slides/` |

A fix to the code is the one change outside the class folder. It goes into the project's history. Change the commit
of the step, and move its tag to the new commit. timewalk keeps working when the tags move between classes.

## Private cues

timewalk shows every line of a notes file. So `just walk-update` leaves your private lines out of the notes that
students get. These lines are private, also when they are indented:

- a line that starts with `> Say:` or `> Note:`, in capitals or not, and with emphasis too, such as `> **Say:**`. Spaces
  before the colon, a list marker before the `>`, and a task box, as in `- [ ] > Say:`, change nothing
- a planned time, `time: m:ss`
- the whole blockquote of a cue, which is every `>` line around the cue, up to a blank line. A line of `>` alone
  counts, and so does a line without a `>` that goes on from the line above it

A line `:::` that opens or closes a block of a tutorial ends the blockquote, and stays. A command line, such as
`$ just test`, ends it too. When a cue sits in an HTML comment, the `-->` of the comment stays.

Every other line goes to students, other `>` cues too. To show a cue to students, start it with another word,
for example `> Try:`. A blockquote with a private cue and a public cue stops `just walk-update`, and `just check`
reports it as an error. Put a blank line between the two cues.

A line in fenced code is code, and goes to students. But `just walk-update` stops on a line in code that would be
private outside the code, such as an example `> Say:`. If the line is code for students, run
`just walk-update --allow-cues-in-code`. `scripts/private.py` is the one place in walk-kit that names the private
lines.

## What walk-update refuses

`just walk-update` writes only into the walk repository. It stops, and writes nothing, in these cases:

- the walk repository has changes that are not committed. The pages that `just pages` wrote do not count
- the walk repository is the class folder or the project, or lies inside or around either one
- the `.git` of the walk repository is a file, a worktree or a submodule
- a path in `toc.toml` is absolute, has a `..`, or would take the place of a file such as `README.md` or `repo/`
- a value in `toc.toml`, such as a `description`, is a private line
- a comment in `toc.toml` or `slides.toml` would be a private line without its `#`, such as `# Say: ...`
- a slide has a private line, a slides folder has a symbolic link, or a PDF is not named in its manifest

It copies the folder of each slides manifest whole, and every file in it goes to students. So keep each manifest in a
folder of its own, such as `slides/`. Notes beside a manifest would go out with their cues, so walk-update refuses
them. walk-update cannot read the speaker notes of an HTML deck, or the text of a PDF.
Keep your cues out of those files.

walk-update also writes the justfile, `README.md`, `AGENTS.md`, `CLAUDE.md`, `.gitignore` and the Pages workflow
of the walk repository from the templates of walk-kit. A file that you changed by hand stays as it is, and
walk-update says so. `just walk-update --replace-edited` makes such a file again from its template.
