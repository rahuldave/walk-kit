"""Refresh a project's walk repository, PROJECT-walk, from the class material, and commit on a yes.

    python3 walk_update.py --project bla --notes notes.md --walk ~/Projects/bla-walk
    python3 walk_update.py ... --slides slides         also copy the slides folder and its manifest
    python3 walk_update.py ... --pdf                   also ship bla.pdf, the slides, one page each; no notes
    python3 walk_update.py ... --repo ~/Projects/bla   the project: the walk repository must not be in it, or around it
    python3 walk_update.py ... --no-commit             write and show, and do not ask to commit
    python3 walk_update.py ... --upstream owner        the project's owner, for the justfile (default: the one it names)
    python3 walk_update.py --project bla --toc toc.toml --walk ~/Projects/bla-walk    a class with several walks

walk.md is the walk's preamble, then the class notes from their first `## ` heading on, without the
private lines that `private.py` names. With --toc, the walk repository gets toc.toml as it is, each walk's notes
made the same way at the same path, and each walk's slides folder. walk.md then goes: the notes of the first walk
are where toc.toml names them. Without --toc, a toc.toml of an earlier update goes, since the walk's justfile
reads it first. The files that walk-init writes, but walk.md, are written again from the templates, so that an old walk
repository gets the new recipes. A file that matches no version of its template was edited by hand: the script says so.

The script writes only into a walk repository. It refuses one that is the class folder, the project, or inside or
around either, by what the folders are on the disk and not by their text. It refuses one whose .git is a file, a
worktree or a submodule, or that has no justfile from walk-init, no walk.md and no toc.toml. It refuses a path in toc.toml
that is absolute, has a `..`, or names a file of the walk repository itself, such as README.md or repo/. Before
each write, it checks that the target is in the walk repository, and is not the repository itself or its .git. It
writes each file as a new file and renames it into place, so a link in the walk repository is replaced, not written through.

A slides folder is the folder of a manifest. The script copies it whole, and nothing else of the class folder. It
refuses a manifest in the class folder itself, or in a folder that holds the notes of a walk: the notes there
have the private lines. It refuses a slides folder with a symbolic link in it, a PDF that is not the file of an entry of
the manifest, or a slides file with a private line. It refuses notes that are a symbolic link, a blockquote with a private
and a public cue, and a toc.toml with a private line in a value. Last, it reads every file that the commit would take,
written or not, and stops before the commit if one has a private line. It also stops on a
line in fenced code that would be private outside it, unless --allow-cues-in-code says that each is code to show.

The script never writes build/walk.pdf, the student's own PDF. It never pushes: it prints the command that does.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

from common import GITHUB, HERE, TEMPLATES, TIMEWALK, UVX, TocError, fill, run, toc_walks, walk_text, yes
from private import MixedCue, in_code, private_lines
from walk_init import FILES

# What walk-init writes, and the folders that its .gitignore names: no path of toc.toml may take their place
OWN = {name.casefold() for name in FILES if name != "walk.md"} | {"toc.toml", ".git"} | {
    found.casefold() for found in re.findall(r"^/([^/\s]+)/$", (TEMPLATES / "walk" / "gitignore").read_text(encoding="utf-8"), re.MULTILINE)}
WALK_MARK = "--replay worktree"  # a line of the walk template's justfile, and of no other justfile


class Refused(Exception):
    """A layout of the class folder that walk-update does not copy, with the reason."""


def main() -> int:  # The exit code
    """Write the walk repository's files, show what changed, and commit on a yes."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--project", required=True, help="the project's name")
    parser.add_argument("--notes", type=Path, help="the class notes, with the private cues")
    parser.add_argument("--toc", type=Path, help="in place of --notes and --slides: the table of contents of several walks")
    parser.add_argument("--walk", required=True, type=Path, help="the walk repository, PROJECT-walk")
    parser.add_argument("--repo", type=Path, help="the project, which the walk repository must not be in or around")
    parser.add_argument("--slides", type=Path, help="a slides folder with slides.toml, to copy there")
    parser.add_argument("--upstream", help="the project's owner on GitHub, for the walk repository's justfile and README "
                        "(default: the one that its justfile names)")
    parser.add_argument("--pdf", action="store_true", help="also ship PROJECT.pdf, the slides as written; with --toc, one for each walk")
    parser.add_argument("--timewalk", default=TIMEWALK, help=f"timewalk for the PDF (default: {TIMEWALK})")
    parser.add_argument("--message", default="The walk, from the class notes", help="the commit message")
    parser.add_argument("--no-commit", action="store_true", help="write and show the diff; do not commit")
    parser.add_argument("--allow-cues-in-code", action="store_true",
                        help="go on when a line in fenced code would be private outside it: each such line is code for students")
    args = parser.parse_args()
    walk = args.walk.expanduser().resolve()
    if bool(args.notes) == bool(args.toc):
        print("walk-update: give --notes, or --toc for a class with several walks", file=sys.stderr)
        return 2
    try:
        check_walk(args, walk)
        args.upstream = upstream_of(args, walk)
        written = toc(args, walk) if args.toc else one(args, walk)
        written += templates(args, walk)
    except (Refused, TocError) as refused:
        print(f"walk-update: {refused}", file=sys.stderr)
        return 2
    found, code = leaks(written)
    if found:
        print("walk-update: these lines in the walk repository are private, so nothing is committed. "
              f"Remove them in the class folder, then run again. {undo(walk)}", file=sys.stderr)
        for place in found:
            print(f"  {place}", file=sys.stderr)
        return 2
    if code and not args.allow_cues_in_code:
        print("walk-update: these lines are in fenced code, and would be private outside it, so nothing is committed. "
              "If each one is code that students should see, run again with --allow-cues-in-code. "
              f"Otherwise check the fences around them. {undo(walk)}", file=sys.stderr)
        for place in code:
            print(f"  {place}", file=sys.stderr)
        return 2
    if args.pdf:
        pdfs(args, walk)
    return finish(args, walk)


def undo(
    walk: Path,  # The walk repository
) -> str:  # The commands that put back its files as committed
    """Say how to throw away what walk-update wrote."""
    return f"To undo the files: git -C {walk} checkout . && git -C {walk} clean -fd"


def within(
    path: Path,  # A path, resolved
    folder: Path,  # A folder, resolved
) -> bool:  # True if the path is the folder or in it, by any spelling of the folder
    """Say whether a path is in a folder: the folder itself or one of the path's parents is the same folder on the disk."""
    # The disk decides: /System/Volumes/Data/x and /x, or an accent written as one character or as two, name one folder on macOS
    try:
        if folder.exists() and any(step.exists() and os.path.samefile(step, folder) for step in [path, *path.parents]):
            return True
    except OSError:
        pass
    # For a path that is not there yet, the text decides: without regard to case or to how an accent is written
    def parts(found: Path) -> list[str]:  # The parts of a path, as a disk that ignores case compares them
        return [unicodedata.normalize("NFC", part).casefold() for part in found.parts]
    inner, outer = parts(path), parts(folder)
    return inner[: len(outer)] == outer


def check_walk(
    args: argparse.Namespace,  # The command line
    walk: Path,  # The walk repository, resolved
) -> None:
    """Refuse a walk repository that is not one: the class folder, the project, a folder around them, or a folder that walk-init did not make."""
    if not (walk / ".git").exists():
        raise Refused(f"{walk} is not a git repository. walk-init makes it")
    if (walk / ".git").is_symlink() or not (walk / ".git").is_dir():
        raise Refused(f"{walk}/.git is not a folder, so {walk} is a worktree or a submodule of another repository. "
                      "Give --walk the walk repository that walk-init made")
    if not re.fullmatch(r"[\w][\w.-]*", args.project):
        raise Refused(f"the project's name {args.project!r} is not a name: give letters, digits, '.', '-' and '_'")
    source = (args.toc or args.notes).expanduser().resolve()
    keep = {"the class folder": source.parent}
    if args.slides:
        keep["the slides folder"] = args.slides.expanduser().resolve()
    if args.repo:
        keep["the project"] = args.repo.expanduser().resolve()
    for name, folder in keep.items():
        if within(walk, folder) or within(folder, walk):
            where = "is" if within(walk, folder) and within(folder, walk) else ("is inside" if within(walk, folder) else "holds")
            raise Refused(f"the walk repository {walk} {where} {name}, {folder}. Give --walk the walk repository that walk-init made, "
                          "a folder of its own beside the class folder")
    tags = subprocess.run(["git", "-C", str(walk), "tag", "-l", "step-*"], capture_output=True, text=True, check=False).stdout
    if tags.strip():
        raise Refused(f"{walk} has tags step-*, so it is the project, not its walk repository. Give --walk the folder that walk-init made")
    justfile = walk / "justfile"
    made = justfile.is_file() and WALK_MARK in justfile.read_text(encoding="utf-8", errors="ignore")
    if not (made or (walk / "walk.md").is_file() or (walk / "toc.toml").is_file()):
        raise Refused(f"{walk} does not look like a walk repository: it has no justfile from walk-init, no walk.md and no toc.toml. "
                      "walk-init makes one")


def target(
    walk: Path,  # The walk repository, resolved
    path: Path,  # A file or folder that the script is about to write, delete or make
) -> Path:  # The same path, once it is known to be safe to write
    """Refuse a write anywhere but in the walk repository: not the repository itself, not its .git, and not through a symbolic link."""
    resolved = path.resolve()
    if path.is_symlink() or not within(resolved, walk) or within(walk, resolved) or within(resolved, walk / ".git"):
        raise Refused(f"refusing to write {path}: it is not a file of the walk repository {walk}")
    return path


def write(
    walk: Path,  # The walk repository, resolved
    path: Path,  # A file of the walk repository
    data: str | bytes,  # What goes in it: text is written as UTF-8
) -> None:
    """Write a file of the walk repository as a new file: a temporary file beside it, then renamed, so that a link is replaced, not written through."""
    path = target(walk, path)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data.encode("utf-8") if isinstance(data, str) else data)
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def upstream_of(
    args: argparse.Namespace,  # The command line
    walk: Path,  # The walk repository, resolved
) -> str:  # The project's owner on GitHub: --upstream, or the one that the walk repository's justfile names
    """Find the upstream owner that the walk repository's justfile and README name."""
    justfile = walk / "justfile"
    old = justfile.read_text(encoding="utf-8", errors="ignore") if justfile.is_file() else ""
    named = re.search(r'^upstream := "([^"]*)"', old, re.MULTILINE)
    upstream = args.upstream or (named.group(1) if named else "")
    if not re.fullmatch(r"[\w][\w.-]*", upstream):
        raise Refused(f"{justfile} names no upstream owner, so the files that walk-init made cannot be made again from its templates. "
                      "Give --upstream OWNER, the project's owner on GitHub")
    return upstream


def templates(
    args: argparse.Namespace,  # The command line
    walk: Path,  # The walk repository, resolved
) -> list[Path]:  # The files written
    """Write the files that walk-init writes, but walk.md, again from the templates, with the values that walk-init gives them."""
    old = (walk / "justfile").read_text(encoding="utf-8", errors="ignore") if (walk / "justfile").is_file() else ""
    # An old justfile names the timewalk of its day. The old templates are filled with it, to tell them from a hand edit
    was = re.search(r'^timewalk := env\("TIMEWALK", "([^"]*)"\)', old, re.MULTILINE)
    values = {"project": args.project, "upstream": args.upstream, "timewalk": GITHUB}
    written = []
    for name, template in FILES.items():
        if name == "walk.md":
            continue
        path = walk / name
        new = fill(template, values)
        if path.is_file() and not path.is_symlink():
            before = path.read_text(encoding="utf-8", errors="ignore")
            if before != new and before not in versions(template, {**values, "timewalk": was.group(1) if was else GITHUB}):
                print(f"walk-update: {name} matches no version of walk-kit's template, so it was edited by hand. It is made again "
                      f"from the template: the diff shows what goes. To keep your text: git -C {walk} checkout HEAD -- {name}")
        write(walk, path, new)
        written.append(path)
    print("walk-update: wrote " + ", ".join(path.name for path in written) + " again from walk-kit's templates")
    return written


def versions(
    template: str,  # A path under templates/, for example "walk/justfile"
    values: dict[str, str],  # What replaces each @key@
) -> set[str]:  # The template filled, as it is and as each commit of walk-kit had it, if walk-kit is a git clone
    """Fill every version of a template that walk-kit knows."""
    found = {fill(template, values)}
    kit, where = HERE.parent, f"templates/{template}"
    log = subprocess.run(["git", "-C", str(kit), "log", "--format=%H", "--", where], capture_output=True, text=True, check=False)
    for commit in log.stdout.split() if log.returncode == 0 else []:
        shown = subprocess.run(["git", "-C", str(kit), "show", f"{commit}:{where}"], capture_output=True, text=True, check=False)
        if shown.returncode == 0:
            text = shown.stdout
            for key, value in values.items():
                text = text.replace(f"@{key}@", value)
            found.add(text)
    return found


def own(
    path: str,  # A path of toc.toml, from its folder
    key: str,  # What it is: the notes, the slides or the folder
    walk_id: str | None,  # The walk that names it
    notes: bool = False,  # True for the notes, which may be walk.md
) -> None:
    """Refuse a path of toc.toml that would take the place of a file of the walk repository itself."""
    first = Path(path).parts[0].casefold()
    if first in OWN or (first == "walk.md" and not (notes and Path(path).parts == ("walk.md",))):
        raise Refused(f"the {key} of walk {walk_id} is {path}, which would take the place of {Path(path).parts[0]} in the walk repository. "
                      "Give it another name in toc.toml")


def links(
    path: Path,  # A file or folder in the class folder, as written, not resolved
    root: Path,  # The class folder
) -> Path | None:  # The first symbolic link on the way from the class folder to the path, or None
    """Find a symbolic link in a path of the class folder."""
    steps = [path] + [step for step in path.parents if step.is_relative_to(root) and step != root]
    return next((step for step in steps if step.is_symlink()), None)


def one(
    args: argparse.Namespace,  # The command line, with --notes
    walk: Path,  # The walk repository
) -> list[Path]:  # The files and folders written into the walk repository
    """Write walk.md, and copy the slides folder to slides/."""
    notes = args.notes.expanduser().absolute()
    if links(notes, notes.parent):
        raise Refused(f"the notes {notes} are a symbolic link. Give the notes file itself")
    notes = notes.resolve()
    written = []
    if args.slides:
        source = args.slides.expanduser().absolute()
        if not (source / "slides.toml").exists():
            raise Refused(f"{args.slides} has no slides.toml")
        check_slides(source, notes.parent, [notes], args.allow_cues_in_code)
        copy_slides(source.resolve(), target(walk, walk / "slides"))
        written.append(walk / "slides")
        print("walk-update: copied the slides and their manifest into slides/")
    if (walk / "toc.toml").is_file():  # of an earlier update with --toc: the walk's justfile reads it before walk.md
        try:
            stale = dropped_walks(walk, [])
        except TocError:
            stale = []
        target(walk, walk / "toc.toml").unlink()
        print("walk-update: removed toc.toml: the class has one walk now, walk.md")
        report_stale(stale)
    text = notes.read_text(encoding="utf-8")
    students, dropped = student_text(text, args.project, notes)
    write(walk, walk / "walk.md", students)
    written.append(walk / "walk.md")
    print(f"walk-update: wrote walk.md, without {dropped} private lines")
    return written


def toc(
    args: argparse.Namespace,  # The command line, with --toc
    walk: Path,  # The walk repository
) -> list[Path]:  # The files and folders written into the walk repository
    """Copy toc.toml, the slides folder of every walk, and then the notes of every walk without the private lines."""
    source = args.toc.expanduser().resolve()
    folder = source.parent
    walks = toc_walks(source)
    toc_cues(source)
    for found in walks:
        for key in ("folder", "notes", "slides"):
            if found[key]:
                own(found[key], key, found["id"], notes=key == "notes")
        if found["notes"] and links(folder / found["notes"], folder):
            raise Refused(f"the notes of walk {found['id']}, {found['notes']}, go through a symbolic link. Give the notes file itself")
    notes = [source] + [(folder / found["notes"]).resolve() for found in walks if found["notes"]]
    with_slides = [found for found in walks if found["slides"] and (folder / found["slides"]).is_file()]
    for found in walks:  # timewalk refuses a toc.toml that names a folder that is not there
        if found["folder"] and not (folder / found["folder"]).is_dir():
            raise Refused(f"walk {found['id']}: its folder {found['folder']} does not exist in {folder}. "
                          "Make it, or take the walk out of toc.toml")
    for found in with_slides:
        check_slides((folder / found["slides"]).parent, folder, notes, args.allow_cues_in_code)
    try:
        stale = dropped_walks(walk, walks)
    except (TocError, Refused) as error:
        print(f"walk-update: the toc.toml of the walk repository cannot be read, so the files of walks that it dropped are not listed: {error}")
        stale = []
    write(walk, walk / "toc.toml", source.read_bytes())
    written = [walk / "toc.toml"]
    print("walk-update: copied toc.toml")
    for found in with_slides:
        slides = Path(found["slides"]).parent
        copy_slides((folder / slides).resolve(), target(walk, walk / slides))
        written.append(walk / slides)
        print(f"walk-update: copied {slides}/, the slides of walk {found['id']}")
    # The notes go last, so that nothing copied before them can stand in their place
    for found in walks:
        if found["notes"] and (folder / found["notes"]).is_file():
            text = (folder / found["notes"]).read_text(encoding="utf-8")
            out = target(walk, walk / found["notes"])
            out.parent.mkdir(parents=True, exist_ok=True)
            students, dropped = student_text(text, args.project, folder / found["notes"])
            write(walk, out, students)
            written.append(out)
            print(f"walk-update: wrote {found['notes']}, without {dropped} private lines")
    # A walk's folder with nothing in it yet: git keeps no empty folder, and timewalk needs the folder
    for found in walks:
        if found["folder"] and not any((walk / found["folder"]).glob("*")):
            target(walk, walk / found["folder"]).mkdir(parents=True, exist_ok=True)
            write(walk, walk / found["folder"] / ".gitkeep", b"")
            print(f"walk-update: made {found['folder']}/ with an empty .gitkeep: walk {found['id']} has no notes or slides yet")
    first = walk / "walk.md"
    if first.exists() and not any(within(first.resolve(), (walk / found["notes"]).resolve()) for found in walks if found["notes"]):
        target(walk, first).unlink()
        print("walk-update: removed walk.md: toc.toml says where the notes of each walk are")
    report_stale(stale)
    return written


def student_text(
    text: str,  # The class notes of a walk
    project: str,  # The project's name
    notes: Path,  # Where the notes are, for the message
) -> tuple[str, int]:  # The notes for students, and the number of private lines dropped
    """Make the students' notes, and refuse a blockquote with a private and a public cue."""
    try:
        return walk_text(text, project)
    except MixedCue as mixed:
        raise Refused(mixed_message(notes, mixed)) from None


def mixed_message(
    file: Path,  # The file with the blockquote
    mixed: MixedCue,  # Where its two cues are
) -> str:  # What to tell the author
    """Say where a blockquote mixes a cue for the presenter with a public cue, and how to part them."""
    return (f"{file}:{mixed.at + 1} is a public cue in the same blockquote as the cue for the presenter at line {mixed.cue + 1}. "
            "The cue's whole blockquote stays in the class folder, so put a blank line between the two cues")


def toc_cues(
    toc: Path,  # The class's toc.toml, which goes to students as it is
) -> None:
    """Refuse a toc.toml with a private line in one of its values, such as a description that starts with > Say:."""
    import tomllib  # toc_walks has read it, so this Python has tomllib

    for value in strings(tomllib.loads(toc.read_text(encoding="utf-8"))):
        try:
            private = private_lines(value)
        except MixedCue:
            private = [0]
        if private:
            raise Refused(f"{toc} has a private line in a value, {value.splitlines()[private[0]]!r}, and toc.toml goes to students as it is. "
                          "Start it with another word")


def report_stale(
    stale: list[str],  # Paths in the walk repository of walks that its toc.toml no longer lists
) -> None:
    """List the files of dropped walks, for the author to delete."""
    if stale:
        print("walk-update: these are of walks that toc.toml no longer lists. Delete them in the walk repository if no walk needs them:")
        for path in stale:
            print(f"  {path}")


def check_slides(
    slides: Path,  # The folder of a manifest, in the class folder, as written
    root: Path,  # The class folder
    notes: list[Path],  # The notes of every walk, and toc.toml: files that must not go with the slides
    allow: bool,  # True to let a line in fenced code through when it would be private outside it
) -> None:
    """Refuse a slides folder that is the class folder, that holds notes, that has a symbolic link or a stray PDF, or that has a private line."""
    root = root.resolve()
    link = links(slides.absolute(), root)
    if link:
        raise Refused(f"the slides folder {slides} goes through a symbolic link, {link}. Put the slides themselves in the folder")
    slides = slides.resolve()
    if within(root, slides) or not within(slides, root):
        raise Refused(f"the manifest in {slides} is not in a slides folder of its own. The class folder holds the notes, "
                      "with their private lines. Put the manifest and its slides in a folder such as slides/")
    inside = [path for path in notes if within(path, slides)]
    if inside:
        raise Refused(f"the slides folder {slides} holds {inside[0].name}, which goes to students only without its private lines. "
                      f"Put the manifest and its slides in a folder of their own, such as {slides.relative_to(root) / 'slides'}/")
    named = manifest_files(slides / "slides.toml")
    for place, folders, files in os.walk(slides):
        folders[:] = [name for name in folders if name != ".git"]
        for name in folders + files:
            path = Path(place) / name
            if path.is_symlink():
                raise Refused(f"the slides folder {slides} has a symbolic link, {path}. Copy the file into the folder in its place")
            if name.lower().endswith(".pdf") and path.relative_to(slides).as_posix() not in named:
                raise Refused(f"the slides folder {slides} has a PDF that its manifest does not name, {path}. "
                              "A PDF can hold the notes, so move it out of the folder, or name it in slides.toml")
    found, code = leaks([slides])
    if found:
        raise Refused("these lines of the slides are private, so the slides cannot go to students. "
                      "Start each with another word, for example > Try:\n  " + "\n  ".join(found))
    if code and not allow:
        raise Refused("these lines of the slides are in fenced code, and would be private outside it. If each one is code that "
                      "students should see, run again with --allow-cues-in-code:\n  " + "\n  ".join(code))


def strings(
    value: object,  # A value read from TOML
) -> list[str]:  # Every string in it, in tables and lists too
    """Find the strings of a TOML value."""
    if isinstance(value, str):
        return [value]
    items = value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
    return [found for item in items for found in strings(item)]


def manifest_files(
    manifest: Path,  # A slides.toml
) -> set[str]:  # The file of each entry, without its #fragment, from the manifest's folder
    """Name the files that a slides manifest shows."""
    text = manifest.read_text(encoding="utf-8", errors="ignore")
    try:
        import tomllib

        entries = strings(tomllib.loads(text))
    except ModuleNotFoundError:  # Python 3.10: every quoted string outside a comment
        entries = [a or b for line in text.splitlines() if not line.lstrip().startswith("#")
                   for a, b in re.findall(r'"([^"]*)"|\'([^\']*)\'', line)]
    except tomllib.TOMLDecodeError as error:
        raise Refused(f"cannot read {manifest}: {error}") from None
    return {os.path.normpath(entry.split("#")[0]) for entry in entries if entry.split("#")[0]}


def copy_slides(
    source: Path,  # A slides folder in the class folder, checked by check_slides
    target: Path,  # The same folder in the walk repository, checked by target()
) -> None:
    """Put a fresh copy of a slides folder in the walk repository."""
    if target.is_dir():
        shutil.rmtree(target)
    elif target.exists():
        target.unlink()
    shutil.copytree(source, target, ignore=shutil.ignore_patterns(".git"))


def dropped_walks(
    walk: Path,  # The walk repository, before its toc.toml is replaced
    walks: list[dict[str, str | None]],  # The walks of the new toc.toml
) -> list[str]:  # The notes, slides folders and folders of walks that the old toc.toml had and the new one has not, outermost only
    """Find what the walk repository still holds of walks that toc.toml dropped."""
    if not (walk / "toc.toml").is_file():
        return []
    kept = {found["id"] for found in walks}
    used = {path for found in walks for path in uses(found)}
    stale = []
    for found in toc_walks(walk / "toc.toml"):
        if found["id"] not in kept:
            stale += [path for path in uses(found) if path not in used and (walk / path).exists()]
    return sorted(path for path in set(stale) if not any(Path(path).is_relative_to(other) for other in set(stale) - {path}))


def uses(
    found: dict[str, str | None],  # One walk of a toc.toml
) -> list[str]:  # Its notes, its slides folder and its folder, as written
    """Name the paths of a walk in the walk repository."""
    paths = [found["notes"], found["folder"]]
    if found["slides"]:
        paths.append(str(Path(found["slides"]).parent))
    return [path for path in paths if path]


def leaks(
    paths: list[Path],  # Files and folders that go to students
) -> tuple[list[str], list[str]]:  # Each private line, as file:line; and each line in fenced code that would be private outside it
    """Read every file, and find the private lines, and the lines in code that look private."""
    found, code = [], []
    for path in paths:
        files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file() and ".git" not in p.relative_to(path).parts)
        for file in files:
            text = file.read_bytes().decode("utf-8", errors="ignore")
            try:
                found += [f"{file}:{at + 1}" for at in private_lines(text)]
            except MixedCue as mixed:
                found.append(mixed_message(file, mixed))
            code += [f"{file}:{at + 1}" for at in in_code(text)]
    return found, code


def pdfs(
    args: argparse.Namespace,  # The command line
    walk: Path,  # The walk repository, with its files written
) -> None:
    """Make the PDF of the slides: PROJECT.pdf, and with --toc PROJECT-ID.pdf for each walk after the first."""
    if not args.toc:
        if (walk / "slides" / "slides.toml").exists():
            target(walk, walk / f"{args.project}.pdf").unlink(missing_ok=True)  # a new file, so that a link is replaced
            run(*UVX, args.timewalk, "timewalk-pdf", "slides/slides.toml", "--notes", "walk.md",
                "--title", args.project, "-o", f"{args.project}.pdf", cwd=walk)
        else:
            print("walk-update: there are no slides, so there is no PDF: the notes are for the step browser")
        return
    walks = toc_walks(walk / "toc.toml")
    with_slides = [found for found in walks if found["slides"] and (walk / found["slides"]).is_file()]
    if not with_slides:
        print("walk-update: no walk has slides, so there is no PDF: the notes are for the step browser")
    for found in with_slides:
        out = f"{args.project}.pdf" if found is walks[0] else f"{args.project}-{found['id']}.pdf"
        target(walk, walk / out).unlink(missing_ok=True)
        run(*UVX, args.timewalk, "timewalk-pdf", "--toc", "toc.toml", "--walk", found["id"], "-o", out, cwd=walk)


def finish(
    args: argparse.Namespace,  # The command line
    walk: Path,  # The walk repository, with its files written
) -> int:  # The exit code
    """Show what changed in the walk repository, and commit it on a yes."""
    run("git", "add", "-A", cwd=walk)
    if subprocess.run(["git", "-C", str(walk), "diff", "--cached", "--quiet"], check=False).returncode == 0:
        print(f"walk-update: {walk.name} has no changes")
        return 0
    # git add -A takes every file of the walk repository, not only those written here: read each one that would be committed
    staged = subprocess.run(["git", "-C", str(walk), "diff", "--cached", "--name-only", "--diff-filter=d", "-z"],
                            capture_output=True, text=True, check=True).stdout.split("\0")
    found, code = leaks([walk / name for name in staged if name and not name.lower().endswith(".pdf")])
    if found or (code and not args.allow_cues_in_code):
        run("git", "reset", "--quiet", cwd=walk)
        print("walk-update: these lines of files in the walk repository are private, or would be private outside fenced code, "
              f"so nothing is committed. Remove them, or the file, in the walk repository, then run again. {undo(walk)}", file=sys.stderr)
        for place in found + (code if not args.allow_cues_in_code else []):
            print(f"  {place}", file=sys.stderr)
        return 2
    run("git", "diff", "--cached", "--stat", cwd=walk)
    run("git", "diff", "--cached", cwd=walk)
    if args.no_commit or not yes(f"walk-update: commit these changes in {walk}?"):
        run("git", "reset", "--quiet", cwd=walk)
        print("walk-update: written, not committed")
        return 0
    run("git", "commit", "--quiet", "-m", args.message, cwd=walk)
    print(f"walk-update: committed. To publish it: git -C {walk} push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
