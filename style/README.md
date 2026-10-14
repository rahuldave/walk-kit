# The writing guide

Everything that the walk skill writes follows `GUIDE.md`, the nossaifd writing guide. The rules live only
in `GUIDE.md`. Other files of walk-kit point to it, and do not repeat them.

`GUIDE.md` and `check.py` are copies from the nossaifd repository, https://github.com/rahuldave/nossaifd, at its
commit 13db27d.
Its site is https://rahuldave.com/nossaifd/. If the guide changes there, copy both files again. Both files
are under the MIT licence, in `LICENSE` in this folder.

## Glossary

The guide asks for a glossary of the project's terms. Use each term in the same way every time.

| Term | Means |
|---|---|
| Walk | One path through the history of the project, with its own notes and slides |
| Narrative | A walk that goes from tag to tag |
| Tutorial | A walk that also stops at each move |
| Step | A tagged commit of the project, `step-NN` |
| Move | A small commit between two tags, `step-NN.k` |
| Do mode | The mode of a tutorial in which the learner makes each move by hand |
| Watch mode | The mode of a tutorial in which timewalk checks out the commit of each move |
| Shared text | The text of the notes outside the blocks `::: do` and `::: watch`, which both modes show |
| Anchor command | A command at the end of a move that checks it. timewalk shows it under "Check it" |
| Apply this file | The words in the notes for a file to take whole. timewalk shows a button, and the pages a link to the file |
| Facts file | The JSON file that `timewalk-export --json` writes for a walk. The pages are made from it |
| The pages that students read | The pages of each walk, on GitHub and on the website of the walk repository, to read without timewalk |
| Read the tutorial | The way of reading the pages that explains each change. It holds what watch mode shows |
| Build it yourself | The way of reading the pages that gives every line to type and every command to run. It holds what do mode shows |
| What changed | The section at the end of each part of the pages: every file of the change, its diff and its links |

The pages that students read never use the terms step, move, commit or Start. Those terms are for the teacher.

## Check the prose

`check.py` runs with `python3`, as the scripts of walk-kit do, with nothing to install. Run it on each Markdown
file, and fix each hard problem:

```
python3 style/check.py README.md SKILL.md WALKS.md AGENTS.md style/README.md templates/*/*.md
python3 style/check.py -v SKILL.md       # also show the soft notes, for a person to judge
```

In a class folder, `just style` runs `scripts/style.py`, which names the files of the class and runs this checker
on them.

The checker reads prose, and skips code, tables and quoted words. `SKILL.md`, in "Write by the guide", lists
the forms of the notes that `just style` leaves out.
