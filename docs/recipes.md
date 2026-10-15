---
title: Recipes
---

Run `just` with no recipe to see the list in any folder. On this page, `bla` is the name of the project. In a
class with `toc.toml`, a recipe that takes an `ID` uses the walk with that id. With no `ID`, it uses the first walk.

## The class folder

| Recipe | What it does |
|---|---|
| `just setup` | Clones the project and `bla-walk` beside the class folder, if they are missing, and says if the skill is missing |
| `just present` | Opens the first walk in timewalk, with your notes and the clock, and prints the address |
| `just present ID` | Opens another walk |
| `just check` | Checks the notes and slides of every walk against the steps, then the pages that students read |
| `just style` | Checks the README, notes, intros and slides against the writing guide, then has a model review the text that changed |
| `just style -v` | The same, and also shows the soft notes, such as a passive verb, for you to judge |
| `just style --all` | The same, but the model reviews each file whole. Run it once when the class takes up the review, and after big edits |
| `just pages` | Makes the pages that students read, into `bla-walk` or `build/pages`, and commits nothing |
| `just follow` | Makes the pages, then follows each Build it yourself page in a scratch clone. Logs go to `build/follow/` |
| `just draft ID` | Prints a draft section for each move of a tutorial that the notes do not have |
| `just draft ID --write` | Adds the drafts to the notes of the tutorial |
| `just pdf` | Makes `build/bla.pdf`, the slides, one page each. The notes are not in it |
| `just pdf ID` | Makes `build/bla-ID.pdf`, the slides of another walk |
| `BRAND=brand/x just pdf` | Makes the PDF with the font, colours, cover and dividers of the brand folder `brand/x` |
| `just check-pdf` | Checks that no slide is cut off in the PDF of `just pdf`. The last words of every slide must be in the text of the PDF |
| `just walk-init` | Makes `bla-walk`, and asks before it creates the public repository on GitHub |
| `just walk-update` | Copies the notes without your cues, and the slides, into `bla-walk`, and makes its pages. Shows the diff, and asks before it commits |
| `just walk-update --pdf` | The same, and also ships the PDF of each walk with slides |
| `just walk-update --replace-edited` | The same, and writes again from its template each file of `bla-walk` that you edited by hand, such as its justfile |
| `just walk-update --allow-cues-in-code` | The same, and lets a line in fenced code that looks like a private cue go to students |

## The version of timewalk

The recipes do not pin timewalk. Each run fetches the newest commit of timewalk from GitHub, which takes about a
second. To run another copy, such as a working copy that you are changing, set `TIMEWALK` to its folder:

```bash
TIMEWALK=~/Projects/timewalk just present
```

## A class made before a recipe

`just walk-update` writes the files of `bla-walk`, and never the justfile of the class. So a class made before a
recipe of walk-kit does not get it. Copy the recipe, such as `style`, `pages` or `follow`, from
`templates/class/justfile` of walk-kit into the class's `justfile`. For the checks of the pages, copy the last lines
of the recipe `check`, from the comment about the pages that students read.

## walk-kit itself

| Recipe | What it does |
|---|---|
| `just test` | Makes the pages of the walks of [timewalk-test](https://github.com/rahuldave/timewalk-test), and follows each Build it yourself page. Every `git check` must pass. It runs the tests in `tests/` first. It calls no model |
| `just style` | Checks `README.md` and `templates/walk/README.md` against the writing guide, then has a model review what changed in them. `just style --all` reviews them whole |
| `just docs` | Builds this website from `docs/` with smalldocs, and serves it at `http://127.0.0.1:8001` |

`just test` expects timewalk-test in `~/Projects/timewalk-test`, or in the folder that `TIMEWALK_TEST` names. Run
`just build` there first.
