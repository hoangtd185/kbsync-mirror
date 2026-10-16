"""Fetch published articles from the Zendesk Help Center API.

Using the API instead of crawling the rendered pages means we only ever receive the
article body: site navigation, headers, footers and widgets never enter the pipeline.
"""

import logging
import re
import time
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

PAGE_SIZE = 100


@dataclass(frozen=True)
class Article:
    id: int
    title: str
    html_url: str
    updated_at: str
    body_html: str

    @property
    def slug(self) -> str:
        """`<id>-<title-words>`, taken from the Zendesk URL so it is stable and unique."""
        tail = self.html_url.rstrip("/").rsplit("/", 1)[-1]
        slug = re.sub(r"[^a-z0-9]+", "-", tail.lower()).strip("-")
        return slug or str(self.id)


def _session() -> requests.Session:
    retry = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        respect_retry_after_header=True,
        allowed_methods=("GET",),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers["User-Agent"] = "kbsync/1.0 (+help-center-mirror)"
    return session


def _get_json(session: requests.Session, url: str, attempts: int = 4) -> dict:
    """GET a page of results. The adapter retries failed connections and 5xx responses;
    this also retries a connection that drops while the body is being read."""
    for attempt in range(1, attempts + 1):
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError) as exc:
            if attempt == attempts:
                raise
            delay = 2**attempt
            log.warning("Fetching %s failed (%s), retrying in %ss (%d/%d)", url, exc, delay, attempt, attempts)
            time.sleep(delay)
    raise AssertionError("unreachable")


def fetch_articles(base_url: str, locale: str, limit: int | None = None) -> list[Article]:
    """Return published articles, most recently updated first, up to `limit`."""
    session = _session()
    url: str | None = (
        f"{base_url}/api/v2/help_center/{locale}/articles.json"
        f"?per_page={PAGE_SIZE}&sort_by=updated_at&sort_order=desc"
    )
    articles: list[Article] = []
    while url and (limit is None or len(articles) < limit):
        data = _get_json(session, url)
        for raw in data["articles"]:
            if raw.get("draft") or not raw.get("body"):
                continue
            articles.append(
                Article(
                    id=raw["id"],
                    title=raw["title"].strip(),
                    html_url=raw["html_url"],
                    updated_at=raw["updated_at"],
                    body_html=raw["body"],
                )
            )
        url = data.get("next_page")
        log.info("Fetched %d articles so far (of %s)", len(articles), data.get("count"))
    return articles[:limit] if limit else articles
