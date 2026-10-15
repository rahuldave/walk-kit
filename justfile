# walk-kit's own checks. TIMEWALK names another timewalk than GitHub's main, a working copy say

# The project of timewalk-test, whose walks the test follows
test_class := env("TIMEWALK_TEST", home_directory() / "Projects/timewalk-test")
# The address on GitHub that timewalk-test's pages link to
test_github := "https://github.com/o/tally"

[private]
default:
    @just --list --unsorted

# Check README.md and templates/walk/README.md against the writing guide: their form, then a review by a model
style:
    python3 style/check.py README.md templates/walk/README.md
    python3 scripts/review.py --class . README.md templates/walk/README.md

# Render the pages of timewalk-test's walks, and follow each Build it yourself page: every git check must pass
test:
    #!/usr/bin/env bash
    set -euo pipefail
    class={{ quote(test_class) }}
    test -d "$class/repo/.git" || { echo "test: $class/repo is missing; run just build in $class" >&2; exit 1; }
    scratch=$(mktemp -d)
    trap 'rm -rf "$scratch"' EXIT
    python3 scripts/render.py --class "$class" --repo "$class/repo" --github {{ quote(test_github) }} --pages "$scratch/pages" > /dev/null
    failed=0
    for page in "$scratch"/pages/walks/*/build.md; do
        id=$(basename "$(dirname "$page")")
        echo "test: walk $id"
        python3 scripts/follow.py "$page" --repo "$class/repo" --work "$scratch/work/$id" || failed=1
    done
    exit "$failed"

# Build the website of walk-kit from docs/ with smalldocs, and serve it at http://127.0.0.1:8001
docs:
    uvx --from 'smalldocs>=0.1.5' smalldocs render docs
    python3 -m http.server -d docs/_site -b 127.0.0.1 8001
