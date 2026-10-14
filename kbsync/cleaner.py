"""Turn Zendesk article HTML into clean, retrieval-friendly Markdown."""

import html
import re

from bs4 import BeautifulSoup, Tag
from markdownify import MarkdownConverter

from .scraper import Article

NOISE_TAGS = ("script", "style", "noscript", "form", "button", "nav", "svg", "header", "footer")
CALLOUT_LABELS = {"NOTE", "NOTES", "IMPORTANT", "TIP", "TIPS", "WARNING", "CAUTION", "INFO"}
# Marketing sign-off appended to most articles; it adds nothing to an answer.
BOILERPLATE = re.compile(r"is the leader in digital signage software|^that[’']s all!?$", re.I)
HEADING = re.compile(r"^h[1-6]$")


def heading_anchor(text: str) -> str:
    """GitHub-style anchor for a Markdown heading."""
    text = re.sub(r"[^\w\- ]", "", text.strip().lower())
    return re.sub(r"\s", "-", text)


def _drop_noise(soup: BeautifulSoup) -> None:
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    for tag in soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6"]):
        if BOILERPLATE.search(tag.get_text(" ", strip=True)):
            tag.decompose()


def _embeds_to_links(soup: BeautifulSoup) -> None:
    for frame in soup.find_all(["iframe", "video"]):
        src = frame.get("src") or (frame.find("source") or {}).get("src")
        if not src:
            frame.decompose()
            continue
        if src.startswith("//"):
            src = "https:" + src
        para = soup.new_tag("p")
        link = soup.new_tag("a", href=src)
        link.string = "Embedded video" if re.search(r"youtube|vimeo|wistia", src) else "Embedded content"
        para.append(link)
        frame.replace_with(para)


def _rewrite_named_anchors(soup: BeautifulSoup) -> None:
    """Zendesk TOCs point at `<a name>` markers or element ids; repoint them at the Markdown heading anchors."""
    targets: dict[str, str] = {}
    for el in soup.find_all(attrs={"id": True}):
        heading = el if HEADING.match(el.name) else el.find_next(HEADING)
        if heading:
            targets.setdefault(el["id"], heading_anchor(heading.get_text(" ", strip=True)))
    for marker in soup.find_all("a", attrs={"name": True}):
        heading = marker.find_next(HEADING)
        if heading:
            targets[marker["name"]] = heading_anchor(heading.get_text(" ", strip=True))
        parent = marker.parent
        marker.decompose()
        if isinstance(parent, Tag) and parent.name == "p" and not parent.get_text(strip=True):
            parent.decompose()
    for link in soup.find_all("a", href=re.compile(r"^#")):
        name = link["href"][1:]
        target = targets.get(name) or targets.get(html.unescape(name))
        if target:
            link["href"] = "#" + target


def _callout_tables_to_quotes(soup: BeautifulSoup) -> None:
    """Single-column "NOTE / IMPORTANT" boxes are layout tables; render them as blockquotes."""
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2 or any(len(r.find_all(["td", "th"])) != 1 for r in rows):
            continue
        label = rows[0].get_text(" ", strip=True).rstrip(":").upper()
        if label not in CALLOUT_LABELS:
            continue
        quote = soup.new_tag("blockquote")
        lead = soup.new_tag("p")
        strong = soup.new_tag("strong")
        strong.string = label.title() + ":"
        lead.append(strong)
        quote.append(lead)
        for row in rows[1:]:
            cell = row.find(["td", "th"])
            for child in list(cell.contents):
                quote.append(child.extract())
        wrapper = table.parent if table.parent and table.parent.name == "figure" else table
        wrapper.replace_with(quote)


class _Converter(MarkdownConverter):
    def convert_img(self, el, text, parent_tags):
        # Drop width/height/title noise; keep only the alt text and source.
        alt = (el.get("alt") or "").replace("\n", " ").strip()
        src = el.get("src") or ""
        return f"![{alt}]({src})" if src else ""


def html_to_markdown(body_html: str) -> str:
    soup = BeautifulSoup(body_html, "html.parser")
    _drop_noise(soup)
    _embeds_to_links(soup)
    _rewrite_named_anchors(soup)
    _callout_tables_to_quotes(soup)
    md = _Converter(
        heading_style="ATX",
        bullets="-",
        escape_underscores=False,
        table_infer_header=True,
    ).convert_soup(soup)
    md = md.replace(" ", " ")
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip() + "\n"


def render_article(article: Article) -> str:
    """Full Markdown document: title, source URL (used for citations), then the body."""
    return (
        f"# {article.title}\n\n"
        f"Article URL: {article.html_url}\n"
        f"Last updated: {article.updated_at}\n\n"
        f"{html_to_markdown(article.body_html)}"
    )
