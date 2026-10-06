"""Check that no slide is cut off in a PDF made from a class folder.

    python3 pdf_check.py build/PROJECT.pdf [--class DIR] [--words N]

Slides that scroll on the screen are shrunk or split when they become pages. This takes each Markdown slide
in `DIR/slides/slides.toml` (default: the current folder), reads the last words of its last line of text,
and looks for them in the text of the PDF. A slide whose last words are missing is reported: look at its page.
It also prints the number of pages and their sizes, so that a PDF with mixed page sizes shows.

A slide that is only a picture has no text to look for, and is skipped. The text is read in the order it was drawn
(`pdftotext -raw`), so that inline code stays in its line. The check needs `pdftotext` and `pdfinfo` (poppler). It uses only the standard library otherwise.
"""

import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 has none
    tomllib = None


def squash(text: str) -> str:
    "Lower case, no Markdown marks, one space between words. Applied to the slides and to the PDF alike."
    text = re.sub(r"[`*_|#>~]", " ", text.lower())
    text = re.sub(r"[^\w\s.,:;()/'\"=<>+\[\]%$-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def norm(markdown: str) -> str:
    "The text of a line of Markdown as it reads in a PDF: no pictures, no link targets, no HTML tags."
    markdown = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", markdown)               # pictures
    markdown = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", markdown)            # links: keep the words
    markdown = re.sub(r"</?(?:img|div|span|br|hr|p|em|strong|b|i|u|a|sup|sub|center|h[1-6])\b[^>]*>", " ", markdown)  # HTML tags, and only these
    return squash(markdown)


def last_words(slide: str, n: int) -> str | None:
    "The last n words of the last line of prose or table in a slide, or None when it has no text."
    lines, fence = [], False
    for line in slide.splitlines():
        if line.startswith("```"):
            fence = not fence
            continue
        if fence or not line.strip() or line.strip() in ("---", "***") or re.match(r"^\s*\|[\s:|-]+\|\s*$", line):
            continue
        if line.startswith("$ "):
            continue
        lines.append(re.sub(r"^\s*([-*+]|\d+[.)])\s+", "", line))   # a list mark is not text in the PDF
    while lines and not norm(lines[-1]):
        lines.pop()
    if not lines:
        return None
    words = norm(lines[-1]).split()
    return " ".join(words[-n:]) if words else None


def load_manifest(path: Path) -> dict[str, list[str]]:
    "The `[slides]` table of the manifest: step name to its entries. Without tomllib, one line for each step."
    text = path.read_text(encoding="utf-8")
    if tomllib:
        return tomllib.loads(text)["slides"]
    section, found = "", {}
    for line in text.splitlines():
        if line.startswith("["):
            section = line.strip().strip("[]")
        elif section == "slides" and (m := re.match(r"^\s*([\w.-]+)\s*=\s*\[(.*)\]\s*(#.*)?$", line)):
            found[m.group(1)] = re.findall(r'"([^"]*)"', m.group(2))
    return found


def slides_of(slides_dir: Path, entry: str) -> list[str]:
    "The slides of a manifest entry such as `04-docs.md#1-6`; [] for a picture or a PDF page."
    name, _, frag = entry.partition("#")
    if not name.endswith(".md"):
        return []
    parts = (slides_dir / name).read_text(encoding="utf-8").split("\n---\n")
    if not frag:
        return parts
    a, _, b = frag.partition("-")
    return parts[int(a) - 1:int(b or a)]


def main() -> int:
    "Check the PDF named on the command line. The exit code is 1 when a slide's last words are missing."
    args = sys.argv[1:]
    options = {a: args[i + 1] for i, a in enumerate(args) if a in ("--class", "--words")}
    pdf = next(a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in options))
    root = Path(options.get("--class", ".")).expanduser()
    n = int(options.get("--words", 6))
    slides_dir = root / "slides"
    text = subprocess.run(["pdftotext", "-raw", pdf, "-"], capture_output=True, text=True, check=True).stdout
    flat = squash(text).replace(" ", "")      # the PDF's text is not Markdown or HTML: no tag stripping
    info = subprocess.run(["pdfinfo", "-f", "1", "-l", "99999", pdf], capture_output=True, text=True).stdout
    sizes = sorted(set(re.findall(r"Page\s+\d+ size:\s+([\d.]+ x [\d.]+) pts", info)))
    pages = re.search(r"Pages:\s+(\d+)", info)
    print(f"{pdf}: {pages.group(1) if pages else '?'} pages; page sizes: {sizes}")
    manifest = load_manifest(slides_dir / "slides.toml")
    checked = missing = 0
    for step, entries in manifest.items():
        for entry in entries:
            for slide in slides_of(slides_dir, entry):
                tail = last_words(slide, n)
                if tail is None:
                    continue
                checked += 1
                if tail.replace(" ", "") not in flat:
                    missing += 1
                    title = slide.strip().splitlines()[0][:50] if slide.strip() else "?"
                    print(f"  MISSING at {step} / {entry}: [{title}] ... {tail}")
    print(f"slides with text checked: {checked}; last words missing from the PDF: {missing}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
