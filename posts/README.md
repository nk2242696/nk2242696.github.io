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
