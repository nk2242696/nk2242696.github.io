# Blog posts (source)

Drop your Word documents here and the site publishes them automatically.

## How to publish a post

1. Write your article in Word and save it as `.docx` in this folder,
   e.g. `posts/tuning-spark-shuffles.docx`.
2. (Optional) Add a sidecar metadata file next to it with the **same base name**
   and a `.meta.yaml` extension to control the title, date, tags, and description:

   ```yaml
   # posts/tuning-spark-shuffles.meta.yaml
   title: "Tuning Spark Shuffles for 300B+ Records/Day"
   date: "2026-07-22"
   description: "How we cut shuffle spill and stabilized a high-volume pipeline."
   tags:
     - Spark
     - Performance
     - Data Engineering
   ```

   If you skip the sidecar, the title is derived from the filename and the date
   defaults to the build date.
3. Commit and push. The **Build blog from Word docs** GitHub Action converts the
   `.docx` to a styled HTML post in `blog/` and regenerates `blog/index.html`.

## Build locally

```powershell
# Requires pandoc on PATH and: pip install pyyaml
python scripts/build_blog.py
```

Generated files land in `blog/` (post HTML + `blog/assets/<slug>/` for images).
Do not edit files in `blog/` by hand — they are overwritten on each build.

## Shared article UI

Change article layout in `templates/post-template.html`, Word cleanup in
`templates/strip-title.lua`, and the listing in `scripts/build_blog.py`.
Shared theme, navigation, focus, and motion behavior lives in `assets/site.css`
and `assets/site.js`. Rebuild after changing a template or the Lua filter.

Up to three opening text paragraphs appear before the contents; posts that
start with a heading use their metadata description instead. Contents open
by default on desktop and collapse on mobile. Article prose is justified with
automatic hyphenation; headings, captions, tables, and code retain their normal
alignment. Fixed Word image dimensions are
removed so diagrams fit the article; **View larger** opens an accessible
full-resolution viewer with scrolling, a Close button, and Escape support.

Run rendering regression checks with the same dependencies as the build:

```bash
python3 -m unittest discover -s tests
```

## Editing the DuckDB article

`duckdb-big-analytics-small-footprint.md` is the editable authoring source.
The matching `.docx` is the publishing input for the existing workflow.
Original diagrams live in `assets/duckdb/` as SVGs with PNG exports embedded
in the Word document. To regenerate after edits, from the repository root:

```bash
# Requires librsvg's rsvg-convert and the normal blog build dependencies.
for name in toolkit vector-pipeline compression-tradeoff; do
  rsvg-convert -o "assets/duckdb/$name.png" "assets/duckdb/$name.svg"
done
(cd posts && pandoc duckdb-big-analytics-small-footprint.md \
  --from markdown --to docx \
  -o duckdb-big-analytics-small-footprint.docx)
python3 scripts/build_blog.py
```

Commit both authoring and publishing sources so automated builds retain edits.

### Reproducing the example and measurements

The article links to `scripts/benchmark_duckdb_blog.py`. From the repository root,
create the example files with only DuckDB installed:

```bash
python3 scripts/benchmark_duckdb_blog.py --generate-only --rows 5000000
```

This creates `events/` and refuses to overwrite an existing directory. Run the
article's Python example from the repository root. Increase `--rows` to change
the input size; supply a different `--directory` to retain previous data.

For the four-engine benchmark on macOS/Linux, `uv` reads pinned dependencies
from the script's inline metadata:

```bash
uv run --python 3.11.16 scripts/benchmark_duckdb_blog.py --reuse \
  --report benchmark-results.json
```

Without `--reuse`, the benchmark first generates a new dataset. The checked-in
observations are in `assets/duckdb/benchmark-results.json`. Imports are outside
the timers; read/filter/aggregate/sort/materialize are inside. Each engine runs
twice in its own process; OS caches are not flushed. RSS is lifetime peak,
including imports. Results are compared with relative tolerance `1e-12` and
absolute tolerance `1e-8` for floating-point currency conversion. The synthetic
input is null-free and this small workload is not a spill benchmark.
