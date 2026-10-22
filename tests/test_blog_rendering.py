import pathlib
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from unittest.mock import patch

from scripts import build_blog


ROOT = pathlib.Path(__file__).resolve().parent.parent


class ImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "img" and attributes.get("src"):
            self.images.append(attributes)


class BlogRenderingTests(unittest.TestCase):
    def render(self, source, reader="markdown", hide_header=False):
        command = [
            "pandoc",
            "--from", reader,
            "--to", "html5",
            "--standalone",
            "--template", str(ROOT / "templates/post-template.html"),
            "--lua-filter", str(ROOT / "templates/strip-title.lua"),
            "--metadata", "title=Test Post",
            "--metadata", "description=A short introduction.",
            "--toc",
        ]
        if hide_header:
            command.extend(["--metadata", "hide-header=true"])
        return subprocess.run(
            command, input=source, capture_output=True, text=True, check=True
        ).stdout

    def test_intro_precedes_contents_without_losing_text_or_headings(self):
        output = self.render(
            "# Test Post\n\n"
            "First opening paragraph.\n\n"
            "**A bold standfirst.**\n\n"
            "Third opening paragraph.\n\n"
            "Fourth paragraph stays in the body.\n\n"
            "## First section\n\nSection body.\n"
        )
        contents = output.index('<details class="article-contents"')
        for text in (
            "First opening paragraph.",
            "A bold standfirst.",
            "Third opening paragraph.",
        ):
            self.assertEqual(output.count(text), 1)
            self.assertLess(output.index(text), contents)
        self.assertGreater(output.index("Fourth paragraph stays in the body."), contents)
        self.assertIn('href="#first-section"', output)
        self.assertIn('<h2 id="first-section">First section</h2>', output)
        self.assertEqual(output.count('<h1'), 1)

    def test_heading_first_post_keeps_heading_and_uses_description(self):
        output = self.render("## Opening section\n\nThe opening explanation.\n")
        self.assertLess(
            output.index("<p>A short introduction.</p>"),
            output.index('<details class="article-contents"'),
        )
        self.assertIn('href="#opening-section"', output)
        self.assertIn('<h2 id="opening-section">Opening section</h2>', output)
        self.assertEqual(output.count("The opening explanation."), 1)

    def test_figures_and_legacy_image_paragraphs_drop_fixed_dimensions(self):
        for reader in ("markdown", "markdown-implicit_figures"):
            with self.subTest(reader=reader):
                output = self.render(
                    "Opening text.\n\n"
                    "![A useful diagram](diagram.png){width=5in height=2in}\n\n"
                    "## Explanation\n\nThe rest of the article.\n",
                    reader=reader,
                )
                parser = ImageParser()
                parser.feed(output)
                self.assertEqual(len(parser.images), 1)
                image = parser.images[0]
                self.assertEqual(image["alt"], "A useful diagram")
                self.assertEqual(image["loading"], "lazy")
                self.assertEqual(image["decoding"], "async")
                for dimension in ("width", "height", "style"):
                    self.assertNotIn(dimension, image)
                self.assertGreater(
                    output.index('src="diagram.png"'),
                    output.index('<details class="article-contents"'),
                )
                if reader == "markdown-implicit_figures":
                    self.assertIn('class="article-figure"', output)

    def test_custom_header_still_has_accessible_title(self):
        output = self.render("**An opening lead.**\n\n## Details\n", hide_header=True)
        self.assertIn('<h1 class="visually-hidden">Test Post</h1>', output)
        self.assertNotIn('<header class="article-header">', output)
        self.assertEqual(output.count("An opening lead."), 1)

    def test_top_level_plain_text_becomes_paragraphs_but_lists_stay_compact(self):
        output = self.render(
            '[Plain [Str "Opening", Space, Str "text."],'
            'Header 2 ("section", [], []) [Str "Section"],'
            'Plain [Str "Body", Space, Str "text."],'
            'BulletList [[Plain [Str "Compact", Space, Str "item."]]]]',
            reader="native",
        )
        self.assertIn("<p>Opening text.</p>", output)
        self.assertIn("<p>Body text.</p>", output)
        self.assertIn("<li>Compact item.</li>", output)
        self.assertNotIn("<li><p>", output)

    def test_generated_heading_ids_are_ascii_and_stable(self):
        output = self.render(
            "**A short lead.**\n\n"
            "**Personas are selected by evidence need \u2014 not by job-title theatre**\n"
        )
        identifier = "personas-are-selected-by-evidence-need-not-by-job-title-theatre"
        self.assertIn(f'href="#{identifier}"', output)
        self.assertRegex(output, rf'<h2\s+id="{identifier}">')
        self.assertNotIn("\ufffd", output)

    def test_listing_escapes_content_and_uses_shared_ui(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(build_blog, "BLOG_DIR", pathlib.Path(directory)):
                build_blog.render_index([{
                    "slug": "example",
                    "title": "A < B & C",
                    "date": "2026-10-21",
                    "reading_time": 2,
                    "description": "Read <this> & that.",
                    "tags": ["SQL & Python"],
                }])
            output = (pathlib.Path(directory) / "index.html").read_text()
        self.assertIn("A &lt; B &amp; C", output)
        self.assertIn("Read &lt;this&gt; &amp; that.", output)
        self.assertIn("SQL &amp; Python", output)
        self.assertIn('href="/assets/site.css"', output)
        self.assertIn('src="/assets/site.js" defer', output)
        self.assertIn('id="main-content" tabindex="-1"', output)
        self.assertIn('class="skip-link"', output)


if __name__ == "__main__":
    unittest.main()
