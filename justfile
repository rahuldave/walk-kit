# walk-kit's own checks. TIMEWALK names another timewalk than GitHub's main, a working copy say

# The project of timewalk-test, whose walks the test follows
test_class := env("TIMEWALK_TEST", home_directory() / "Projects/timewalk-test")
# The address on GitHub that timewalk-test's pages link to
test_github := "https://github.com/rahuldave/tally"
# The walk repository on GitHub whose pages just test-github follows and checks
test_walk := "https://github.com/rahuldave/tally-walk"

[private]
default:
    @just --list --unsorted

# Check README.md and templates/walk/README.md against the writing guide: their form, then a review by a model. --all reviews them whole
style *args:
    python3 style/check.py README.md templates/walk/README.md
    python3 scripts/review.py --class . {{ args }} README.md templates/walk/README.md

# Render the pages of timewalk-test's walks, follow each Build it yourself page (every git check must pass), and check each page to read
test:
    #!/usr/bin/env bash
    set -euo pipefail
    source={{ quote(test_class) }}
    test -f "$source/history/build.py" || { echo "test: $source is not timewalk-test; set TIMEWALK_TEST" >&2; exit 1; }
    scratch=$(mktemp -d)
    trap 'rm -rf "$scratch"' EXIT
    # walk-kit's copy of the writing guide's checker must be nossaifd's, when a clone of nossaifd is here
    if [ -d ../nossaifd ]; then python3 scripts/style_sync.py; fi
    python3 -m unittest discover -s tests
    # timewalk-test as last committed, with its project built there: an edit in progress or a just build in timewalk-test
    # during the run cannot change the pages under the checks
    class="$scratch/class"
    git clone -q --no-local "$source" "$class"
    python3 "$class/history/build.py" "$class/repo" > /dev/null
    python3 scripts/render.py --class "$class" --repo "$class/repo" --github {{ quote(test_github) }} --pages "$scratch/pages" > /dev/null
    failed=0
    for page in "$scratch"/pages/walks/*/build.md; do
        id=$(basename "$(dirname "$page")")
        echo "test: walk $id"
        python3 scripts/follow.py "$page" --repo "$class/repo" --work "$scratch/work/$id" || failed=1
    done
    # Each part page of each walk's website, as a student who starts at that part
    for page in "$scratch"/pages/site/build/*.qmd "$scratch"/pages/site/*/build/*.qmd; do
        [ -f "$page" ] || continue
        name=$(basename "$(dirname "$(dirname "$page")")")-$(basename "$page" .qmd)
        echo "test: part page $name"
        python3 scripts/follow.py "$page" --repo "$class/repo" --work "$scratch/work/part-$name" > /dev/null || { echo "test: FAIL $name"; failed=1; }
    done
    # Each page to read, Read the tutorial and a narrative's, on GitHub and on the website: nothing to run, every move, every link
    shopt -s nullglob
    echo "test: the pages to read"
    python3 scripts/read_check.py "$scratch"/pages/walks/*/read.md "$scratch"/pages/site/read/*.qmd "$scratch"/pages/site/*/read/*.qmd \
        --repo "$class/repo" --toc "$class/toc.toml" || failed=1
    exit "$failed"

# Follow every Build it yourself page and check every page to read of the walk repository on GitHub, against GitHub itself
test-github walk=test_walk:
    #!/usr/bin/env bash
    set -euo pipefail
    scratch=$(mktemp -d)
    trap 'rm -rf "$scratch"' EXIT
    git clone -q {{ quote(walk) }} "$scratch/walk"
    project=$(sed -nE 's/^project := "(.*)"$/\1/p' "$scratch/walk/justfile")
    upstream=$(sed -nE 's/^upstream := "(.*)"$/\1/p' "$scratch/walk/justfile")
    git clone -q "https://github.com/$upstream/$project" "$scratch/repo"
    pages="$scratch/walk"
    failed=0
    shopt -s nullglob
    for page in "$pages"/walks/*/build.md; do
        id=$(basename "$(dirname "$page")")
        echo "test-github: walk $id"
        python3 scripts/follow.py "$page" --repo "$scratch/repo" --work "$scratch/work/$id" --github 2>&1 | tail -1 || { echo "test-github: FAIL $id"; failed=1; }
    done
    for page in "$pages"/site/build/*.qmd "$pages"/site/*/build/*.qmd; do
        name=$(basename "$(dirname "$(dirname "$page")")")-$(basename "$page" .qmd)
        echo "test-github: part page $name"
        python3 scripts/follow.py "$page" --repo "$scratch/repo" --work "$scratch/work/part-$name" --github 2>&1 | tail -1 || { echo "test-github: FAIL $name"; failed=1; }
    done
    echo "test-github: the pages to read"
    python3 scripts/read_check.py "$pages"/walks/*/read.md "$pages"/site/read/*.qmd "$pages"/site/*/read/*.qmd \
        --repo "$scratch/repo" --github || failed=1
    exit "$failed"

# Build the website of walk-kit from docs/ with smalldocs, and serve it at http://127.0.0.1:8001
docs:
    uvx --from 'smalldocs>=0.3.3' smalldocs render docs
    python3 -m http.server -d docs/_site -b 127.0.0.1 8001
