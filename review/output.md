You check a page that students follow, against what really happened when its commands ran.

The page is a Build it yourself page, under the heading PAGE below. A program followed it as a student would. It ran
each command of the page's bash blocks in a fresh clone of the project, in order. The log, under the heading LOG at
the end, gives each command, what it printed, and its exit code. Your working folder is that clone, after the last
command, and your tools can read it.

Read the page's prose. Find each claim about what a command prints or does, and each number and each output that
the text shows. Examples are "It prints `tally: nothing to count yet`", "the test fails", "2000 words", and "the
three most common words are the, a and of". Compare each one with the log.

Report a claim when the log shows something else, or when no output in the log shows it. Do not report:

- a claim that the log shows, in other words or in part
- a command that fails on purpose, when the text says that it fails
- a claim about a file, which you can check in the clone, when the file agrees
- the sections What changed, the diffs, and the links
- a matter of style. Another review checks the writing

A command's output can differ in small ways from run to run, such as a time, a path or the order of a set. Report such
a difference only when a student would be misled by it.

Give each finding the words of the page at fault, as written. Then say what the log shows instead, or that no output in
the log shows the claim. The verdict is "pass", with no findings, when every claim agrees with the log.
