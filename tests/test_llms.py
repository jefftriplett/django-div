"""llms.txt, llms-full.txt, and the per-page Markdown twins.

The generator reads rendered HTML, so these tests feed it HTML directly
rather than shelling out to a site build. The HTML-to-Markdown conversion
itself lives in django_div.markdown and is tested there; these cover what
the script adds on top — article selection, pruning, and configuration.
"""

import pytest

from scripts.gen_llms import config, convert, nav_order, site_url


def markdown(html: str) -> str:
    return convert(f"<article>{html}</article>")[1]


# --- extraction -------------------------------------------------------------


def test_heading_becomes_the_title():
    title, _ = convert("<article><h1>Building HTML</h1><p>Body.</p></article>")
    assert title == "Building HTML"


def test_page_without_an_article_converts_to_nothing():
    assert convert("<html><body><p>chrome only</p></body></html>") == (None, "")


def test_headings_keep_their_level():
    assert "## Attributes" in markdown("<h2>Attributes</h2>")


def test_nav_and_scripts_are_dropped():
    out = markdown(
        "<nav><a href='/x'>Skip</a></nav><script>var x=1</script><p>Kept</p>"
    )
    assert "Skip" not in out
    assert "var x" not in out
    assert "Kept" in out


def test_permalink_anchors_are_dropped():
    out = markdown('<h2>Attributes<a class="headerlink" href="#a">¶</a></h2>')
    assert "¶" not in out
    assert "## Attributes" in out


def test_code_blocks_keep_language_and_indentation():
    out = markdown(
        '<div class="language-python highlight">'
        "<pre><code>def home():\n    return Div()\n</code></pre></div>"
    )
    assert "```python" in out
    assert "    return Div()" in out, "indentation must survive"


def test_links_become_markdown():
    assert "[docs](/docs/)" in markdown('<p><a href="/docs/">docs</a></p>')


def test_lists_become_bullets():
    out = markdown("<ul><li>one</li><li>two</li></ul>")
    assert "- one" in out
    assert "- two" in out


def test_tables_become_markdown_tables():
    out = markdown(
        "<table><thead><tr><th>Python</th><th>HTML</th></tr></thead>"
        "<tbody><tr><td>class_</td><td>class</td></tr></tbody></table>"
    )
    assert "| Python | HTML |" in out
    assert "| --- | --- |" in out
    assert "| class_ | class |" in out


def test_definition_lists_stay_attached():
    out = markdown("<dl><dt>is_void</dt><dd>Whether it self-closes.</dd></dl>")
    assert "is_void\n:   Whether it self-closes." in out


# --- configuration ----------------------------------------------------------


def test_nav_order_matches_the_config():
    assert nav_order(config())[0] == "index"


def test_every_nav_page_exists():
    from scripts.gen_llms import ROOT

    for slug in nav_order(config()):
        assert (ROOT / "docs" / f"{slug}.md").is_file()


def test_site_url_has_no_trailing_slash():
    assert not site_url(config()).endswith("/")


def test_site_url_can_be_overridden(monkeypatch):
    monkeypatch.setenv("SITE_URL", "http://localhost:8000/preview/")
    assert site_url(config()) == "http://localhost:8000/preview"


@pytest.mark.parametrize("key", ["site_name", "site_description", "repo_url"])
def test_config_has_what_the_generator_needs(key):
    assert config()[key]
