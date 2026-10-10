"""Which lines of the class notes are private: the one place that says so.

The class notes hold the script of every step and the presenter's own cues. timewalk shows every line
of a notes file, cues included, so `walk-update` leaves these lines out of the walk repository:

- a cue for the presenter: a line that starts with `> Say:` or `> Note:`. Also when it is indented, in a list
  item, in a quote inside a quote, in any case (`> say:`), with emphasis (`> **Say:**`), or in an HTML comment on
  one line (`<!-- > Say: ... -->`)
- the whole blockquote of the cue: every line from its first `>` line on that starts with `>`, a line of `>` alone
  too, and the lines that go on the paragraph without a `>`, up to a blank line. Lines before the cue in the same
  blockquote go too. A line without a `>` that starts a block of its own ends the blockquote, and stays: a heading, a
  fence, a list item, HTML, a command or a planned time. A line with `-->` ends it too. It goes with the cue, but its
  `-->` stays, so that an HTML comment around a cue is still closed
- a planned time: a line `time: m:ss`, also when it is indented. Only the presenter's clock band uses it

A line inside a fenced code block is code, and is not dropped. A fence is as CommonMark reads it: at most 3 spaces
before it, three or more backticks or tildes, no backtick after backticks on the opening line, and a closing line of
the same character, at least as long, with nothing after it. `in_code` finds a line in a fence that would be private
outside it. `walk-update` stops on such a line, because a fence that the author reads another way would let a cue
through. Every other line goes to students as written, other `> ` cues included, and `> Note that` or `> Notes:`
too. To make a cue public, start it with another word, for example `> Try:`.

A blockquote with a cue for the presenter and a public cue, such as `> Try:` or any `> Word:`, is refused with
`MixedCue`: it cannot go in part. Put a blank line between the two cues.
"""

import re

CUE = r"(?:>\s*)+[*_]{0,2}(?:say|note)[*_]{0,2}:"  # > Say:, > > note:, > **Say:**, > **Note**:
PRIVATE = [
    re.compile(r"^\s*(?:(?:[-*+]|\d+[.)])\s+)?" + CUE, re.IGNORECASE),  # the presenter's cues
    re.compile(r"^\s*<!--\s*" + CUE, re.IGNORECASE),  # a cue in an HTML comment on one line
    re.compile(r"^\s*time:\s*\d+:\d\d\s*$"),  # the planned start of a step
]
OPEN = re.compile(r"^ {0,3}(`{3,}(?=[^`]*$)|~{3,})")  # a line that opens a fenced code block
CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})\s*$")  # a line that can close one
QUOTED = re.compile(r"^\s*(?:(?:[-*+]|\d+[.)])\s+)?>")  # a line of a blockquote
LABEL = re.compile(r"^\s*(?:(?:[-*+]|\d+[.)])\s+)?(?:>\s*)+[*_]{0,2}[A-Z][A-Za-z]*[*_]{0,2}:")  # a cue of one word, such as > Try:
# A line that starts a block of its own, so it does not go on a paragraph: a heading, a fence, a list item, a
# thematic break, HTML, a command for a terminal, or a planned time. It ends a blockquote when it has no `>`
NEW_BLOCK = re.compile(r"^\s*(?:#{1,6}(?:\s|$)|```|~~~|[-*+]\s|\d+[.)]\s|(?:---|\*\*\*|___)\s*$|<|(?:main|runs[2-9]?)?\$\s|time:)")


def fenced(
    lines: list[str],  # The lines of a Markdown file
) -> set[int]:  # The index of each line of a fenced code block, its two fence lines included
    """Find the lines of fenced code, as CommonMark reads them. A fence that is never closed runs to the end."""
    found, fence = set(), None
    for at, line in enumerate(lines):
        if fence is None:
            mark = OPEN.match(line)
            if mark:
                fence = mark.group(1)
                found.add(at)
            continue
        found.add(at)
        close = CLOSE.match(line)
        if close and close.group(1)[0] == fence[0] and len(close.group(1)) >= len(fence):
            fence = None
    return found


class MixedCue(ValueError):
    """A blockquote with a cue for the presenter and a public cue, which cannot go to students in part."""

    def __init__(
        self,
        at: int,  # The index of the public cue's line, from 0
        cue: int,  # The index of the private cue's line, from 0
    ) -> None:
        super().__init__(f"line {at + 1} is a public cue in the blockquote of the cue for the presenter at line {cue + 1}")
        self.at, self.cue = at, cue


def private_lines(
    text: str,  # The class notes, or any file that goes to students
) -> list[int]:  # The index of each line to drop, from 0: the private lines, and the whole blockquote of each cue
    """Find the lines for the presenter alone, outside fenced code. Raises `MixedCue` for a blockquote with a private and a public cue."""
    lines = text.split("\n")
    code = fenced(lines)
    found, at = set(), 0
    while at < len(lines):
        line = lines[at]
        if at in code or not (QUOTED.match(line) or PRIVATE[1].match(line)):
            if at not in code and PRIVATE[2].match(line):
                found.add(at)
            at += 1
            continue
        # A blockquote, or a comment with a cue: up to a blank line, code, a line that starts a block without a `>`, or past a `-->`
        block = [at]
        while "-->" not in lines[block[-1]]:
            after = block[-1] + 1
            if after >= len(lines) or after in code or not lines[after].strip() or (not QUOTED.match(lines[after]) and NEW_BLOCK.match(lines[after])):
                break
            block.append(after)
        cues = [found_at for found_at in block if PRIVATE[0].match(lines[found_at]) or PRIVATE[1].match(lines[found_at])]
        if cues:
            labels = [found_at for found_at in block if LABEL.match(lines[found_at]) and found_at not in cues]
            if labels:
                raise MixedCue(labels[0], cues[0])
            found.update(block)
        at = block[-1] + 1
    return sorted(found)


def in_code(
    text: str,  # A file that goes to students
) -> list[int]:  # The index of each line, from 0, in fenced code, that would be private outside it
    """Find the lines in fenced code that have the form of a private line."""
    lines = text.split("\n")
    return sorted(at for at in fenced(lines) if any(rule.match(lines[at]) for rule in PRIVATE))


def public(
    text: str,  # The class notes
    start: int = 0,  # The index of the first line to keep, from 0: the lines before it go too
) -> str:  # The same notes without the private lines, and with no run of blank lines left behind
    """Drop the private lines and the extra blank lines they leave, keeping the `-->` of a comment that a kept line opened."""
    drop = set(private_lines(text))
    kept, comment = [], False  # comment: a kept line opened an HTML comment that is not closed yet
    for at, line in enumerate(text.split("\n")):
        if at < start:
            continue
        if at not in drop:
            kept.append(line)
            if "<!--" in line or "-->" in line:
                comment = line.rfind("<!--") > line.rfind("-->") or (comment and "-->" not in line)
        elif comment and "-->" in line:
            kept.append(re.match(r"\s*", line).group() + "-->")
            comment = False
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept))
