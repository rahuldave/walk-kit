"""Which lines of the class notes are private: the one place that says so.

The class notes hold the script of every step and the presenter's own cues. timewalk shows every line
of a notes file, cues included, so `walk-update` leaves these lines out of the walk repository's `walk.md`:

- a cue for the presenter: a line that starts with `> Say:` or `> Note:`
- a planned time: a line `time: m:ss`, which only the presenter's clock band uses

Every other line goes to students as written, other `> ` cues included. To make a cue public, start it
with another word, for example `> Try:`.
"""

import re

PRIVATE = [
    re.compile(r"^> (Say|Note):"),  # the presenter's cues
    re.compile(r"^time:\s*\d+:\d\d\s*$"),  # the planned start of a step
]


def is_private(
    line: str,  # One line of the class notes
) -> bool:  # True if the line stays in the class material
    """Say whether a line of the notes is for the presenter alone."""
    return any(rule.match(line) for rule in PRIVATE)


def public(
    text: str,  # The class notes, from the first `## ` heading on
) -> str:  # The same notes without the private lines, and with no run of blank lines left behind
    """Drop the private lines, and the extra blank lines they leave."""
    kept = [line for line in text.split("\n") if not is_private(line)]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept))
