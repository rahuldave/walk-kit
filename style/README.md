# The writing guide

Everything that the walk skill writes follows `GUIDE.md`, the nossaifd writing guide. The rules live only
in `GUIDE.md`. Other files of walk-kit point to it, and do not repeat them.

`GUIDE.md` and `check.py` are copies from the nossaifd repository, https://github.com/rahuldave/nossaifd, at its
commit 13db27d.
Its site is https://rahuldave.com/nossaifd/. If the guide changes there, copy both files again. Both files
are under the MIT licence, in `LICENSE` in this folder.

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
