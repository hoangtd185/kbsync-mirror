from kbsync.cleaner import heading_anchor, html_to_markdown, render_article
from kbsync.scraper import Article


def test_headings_code_and_relative_links_survive():
    md = html_to_markdown(
        '<h2>Set up</h2><p>Open <a href="/hc/en-us/articles/1-Foo">Foo</a> and run <code>adb install</code>.</p>'
        "<pre>line one\nline two</pre>"
    )
    assert "## Set up" in md
    assert "[Foo](/hc/en-us/articles/1-Foo)" in md
    assert "`adb install`" in md
    assert "```\nline one\nline two\n```" in md


def test_toc_anchor_points_at_markdown_heading():
    md = html_to_markdown(
        '<ul><li><a href="#WhatYoullNeed">What You\'ll Need</a></li></ul>'
        '<p><a name="WhatYoullNeed"></a></p><h2 id="h_01X">What You\'ll Need</h2>'
    )
    assert "[What You'll Need](#what-youll-need)" in md
    assert "WhatYoullNeed" not in md


def test_toc_anchor_with_encoded_ampersand_and_element_id():
    md = html_to_markdown(
        '<a href="#Playlist&amp;amp;Schedule">Go</a>'
        '<a href="#Create">Create</a>'
        '<h2 id="Playlist&amp;Schedule">Playlist &amp; Schedule</h2><h3 id="Create">Create Your Own</h3>'
    )
    assert "(#playlist--schedule)" in md
    assert "(#create-your-own)" in md


def test_callout_table_becomes_blockquote():
    md = html_to_markdown(
        "<figure class='wysiwyg-table'><table><tbody>"
        "<tr><td><p><strong>NOTE</strong></p></td></tr>"
        "<tr><td>Schedule only is normal.</td></tr>"
        "</tbody></table></figure>"
    )
    assert "> **Note:**" in md
    assert "> Schedule only is normal." in md
    assert "|" not in md


def test_data_table_kept_as_markdown_table():
    md = html_to_markdown("<table><thead><tr><th>A</th><th>B</th></tr></thead><tbody><tr><td>1</td><td>2</td></tr></tbody></table>")
    assert "| A | B |" in md and "| 1 | 2 |" in md


def test_noise_and_marketing_footer_removed():
    md = html_to_markdown(
        "<script>track()</script><style>p{}</style><p>Real content.</p>"
        "<h3><span>That’s all!</span></h3>"
        '<p>OptiSigns is the leader in <a href="https://www.optisigns.com/">digital signage software</a>.</p>'
    )
    assert md == "Real content.\n"


def test_iframe_becomes_link_and_images_keep_alt():
    md = html_to_markdown(
        '<iframe src="//www.youtube.com/embed/abc"></iframe>'
        '<img src="https://x/img.png" alt="Apps button" width="430" height="343">'
    )
    assert "[Embedded video](https://www.youtube.com/embed/abc)" in md
    assert "![Apps button](https://x/img.png)" in md


def test_render_article_has_title_and_citation_url():
    article = Article(1, "How to Foo", "https://support.example.com/hc/en-us/articles/1-How-to-Foo", "2026-01-01T00:00:00Z", "<p>Body</p>")
    text = render_article(article)
    assert text.startswith("# How to Foo\n\nArticle URL: https://support.example.com/hc/en-us/articles/1-How-to-Foo\n")
    assert article.slug == "1-how-to-foo"


def test_heading_anchor_matches_github_style():
    assert heading_anchor("What You'll Need") == "what-youll-need"


def test_inline_base64_image_is_dropped_but_alt_kept():
    md = html_to_markdown('<p>Scan it:</p><img src="data:image/png;base64,' + "A" * 5000 + '" alt="QR code">')
    assert "base64" not in md
    assert "*[Image: QR code]*" in md
