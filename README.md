# Nikhil Kumar — Portfolio

Personal portfolio site hosted on GitHub Pages: **https://nk2242696.github.io/**

Big Data Engineer & Cloud Architect with **8+ years** designing and scaling data
platforms across Azure, AWS, and GCP.

## About

A single-page, dependency-free portfolio built with plain HTML, CSS, and vanilla
JavaScript — no build step, no framework, no external runtime libraries. Everything
is served as static files: [index.html](index.html) and shared UI assets in
[`assets/site.css`](assets/site.css) and [`assets/site.js`](assets/site.js).

The portfolio and blog share system-aware light/dark themes, keyboard focus
styles, skip links, and reduced-motion support. Compact screens get a
collapsible navigation menu; articles keep prose narrow while allowing wider
diagrams, tables, and code.

## Highlights

- **Languages:** Java, Python, SQL, Scala
- **Big Data & Streaming:** Apache Spark, Kafka, Hadoop, HBase, HDFS
- **Cloud:** Azure, AWS, GCP, Snowflake
- **Platforms:** Databricks, Azure Synapse, Azure Data Factory, Matillion
- **Databases:** MySQL, PostgreSQL, MongoDB, CosmosDB, Netezza, Oracle
- **DevOps & Monitoring:** Docker, Jenkins, Git, ELK Stack, Kibana

## Experience

| Company | Role | Period |
| --- | --- | --- |
| Microsoft | Software Engineer | Aug 2022 – Present |
| Epsilon | Software Engineer 2 | Jun 2021 – Aug 2022 |
| HashMap Inc | Cloud Data Engineer | Jun 2018 – Jun 2021 |

## Education

- B.Tech in Computer Science — Army Institute of Technology (2014–2018)

## Local preview

Serve the repository root with any static server so shared assets and blog links
resolve correctly:

```powershell
# Requires Python
python -m http.server 8000
# then visit http://localhost:8000
```

## Project structure

```
index.html                     # portfolio markup and page-specific styles
sitemap.xml, robots.txt        # SEO
blog/                          # generated blog (index.html + post HTML)
posts/                         # source Word docs (.docx) + optional .meta.yaml
templates/post-template.html   # Pandoc template for blog posts
templates/strip-title.lua      # Word cleanup, introduction, and image normalization
scripts/build_blog.py          # docx -> HTML build script
tests/test_blog_rendering.py   # Pandoc and listing regression checks
.github/workflows/blog.yml     # auto-publishes posts on push
img/                           # profile photo, company logos
assets/                        # shared UI CSS/JS, resume, and original diagrams
LICENSE                        # MIT
```

> To enable the **Download Resume** button, drop your PDF at
> `assets/Nikhil_Kumar_Resume.pdf`.

## Blog (Word → published post)

Write in Word, save a `.docx` into `posts/`, and push. A GitHub Action runs
[Pandoc](https://pandoc.org/) to convert it into a styled post under `blog/`
that matches the portfolio design (TOC, reading time, tags, syntax-highlighted
code). See [posts/README.md](posts/README.md) for the optional metadata sidecar
format and how to build locally.

The homepage's **Selected Writing** cards are curated in `index.html`; update
their links and metadata when changing featured articles.

```powershell
# Build locally (requires pandoc on PATH and: pip install pyyaml)
python scripts/build_blog.py
```

## Contact

- **Email:** nk2242696@gmail.com
- **LinkedIn:** https://www.linkedin.com/in/nikhil-k-82b003ba/
- **GitHub:** https://github.com/nk2242696

## License

Released under the [MIT License](LICENSE).
