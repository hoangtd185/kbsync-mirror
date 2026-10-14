"""Daily job: re-scrape the help center, then upload only new/changed articles to Gemini File Search.

    python main.py               # scrape + sync
    python main.py --scrape-only # just write Markdown to ./articles
"""

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from kbsync.cleaner import render_article
from kbsync.config import Settings
from kbsync.scraper import fetch_articles
from kbsync.sync import LocalDoc, SyncPlan, content_hash, estimate_chunks, plan_sync

log = logging.getLogger("kbsync")


def write_markdown(settings: Settings) -> tuple[list[LocalDoc], bool]:
    articles = fetch_articles(settings.help_center_url, settings.locale, settings.max_articles)
    full_scrape = settings.max_articles is None
    out = settings.articles_dir
    out.mkdir(parents=True, exist_ok=True)

    docs = []
    for article in articles:
        text = render_article(article)
        path = out / f"{article.slug}.md"
        path.write_text(text, encoding="utf-8")
        docs.append(
            LocalDoc(
                article_id=str(article.id),
                title=article.title,
                url=article.html_url,
                updated_at=article.updated_at,
                path=path,
                content_hash=content_hash(text),
            )
        )
    if full_scrape:
        keep = {d.path.name for d in docs}
        for stale in out.glob("*.md"):
            if stale.name not in keep:
                stale.unlink()
    log.info("Wrote %d Markdown files to %s", len(docs), out)
    return docs, full_scrape


def apply_plan(store, plan: SyncPlan, workers: int) -> list[str]:
    def add(doc):
        store.upload(doc)

    def update(doc, old):
        # Upload first so the article never disappears from the store if the upload fails.
        store.upload(doc)
        for remote in old:
            store.delete(remote)

    jobs = [(add, (d,), d.article_id) for d in plan.to_add]
    jobs += [(update, (d, old), d.article_id) for d, old in plan.to_update]
    jobs += [(store.delete, (r,), r.article_id) for r in plan.to_remove]

    failures = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fn, *args): ref for fn, args, ref in jobs}
        for done, future in enumerate(as_completed(futures), 1):
            try:
                future.result()
            except Exception as exc:  # keep going; report at the end
                failures.append(futures[future])
                log.error("Article %s failed: %s", futures[future], exc)
            if done % 25 == 0:
                log.info("Progress: %d/%d", done, len(jobs))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scrape-only", action="store_true", help="write Markdown, skip the upload")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    settings = Settings.from_env()
    started = time.monotonic()

    docs, full_scrape = write_markdown(settings)
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "articles_scraped": len(docs),
    }

    if args.scrape_only:
        log.info("--scrape-only: skipping upload")
    else:
        if not settings.api_key:
            log.error("Set GEMINI_API_KEY (or API_KEY) to upload; see .env.sample")
            return 2
        from kbsync.store import FileSearchStore

        store = FileSearchStore(
            settings.api_key,
            settings.store_display_name,
            settings.max_tokens_per_chunk,
            settings.max_overlap_tokens,
        )
        plan = plan_sync(docs, store.list_documents(), prune=full_scrape)
        log.info(
            "Plan: %d to add, %d to update, %d unchanged, %d to remove",
            len(plan.to_add), len(plan.to_update), len(plan.unchanged), len(plan.to_remove),
        )
        failures = apply_plan(store, plan, settings.upload_workers)

        def chunks(items):
            return sum(
                estimate_chunks(d.path.read_text(encoding="utf-8"), settings.max_tokens_per_chunk, settings.max_overlap_tokens)
                for d in items
            )

        uploaded = [d for d in plan.to_add if d.article_id not in failures]
        uploaded += [d for d, _ in plan.to_update if d.article_id not in failures]
        report.update(
            store=store.name,
            added=len(plan.to_add),
            updated=len(plan.to_update),
            skipped=len(plan.unchanged),
            removed=len(plan.to_remove),
            failed=len(failures),
            failed_article_ids=failures,
            files_embedded=len(uploaded),
            chunks_embedded_estimate=chunks(uploaded),
            chunks_in_store_estimate=chunks(docs),
            chunking={"max_tokens_per_chunk": settings.max_tokens_per_chunk, "max_overlap_tokens": settings.max_overlap_tokens},
        )

    report["duration_s"] = round(time.monotonic() - started, 1)
    settings.report_path.parent.mkdir(parents=True, exist_ok=True)
    settings.report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log.info("Run summary: %s", json.dumps(report))
    return 1 if report.get("failed") else 0


if __name__ == "__main__":
    sys.exit(main())
