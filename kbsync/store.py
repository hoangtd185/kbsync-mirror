"""Thin wrapper over the Gemini File Search store API.

Sync state lives on the documents themselves (`custom_metadata`), so the job is stateless:
any run, on any machine, can work out the delta by listing the store.
"""

import logging
import time

from google import genai
from google.genai import errors, types

from .sync import LocalDoc, RemoteDoc

log = logging.getLogger(__name__)

RETRYABLE = {429, 500, 502, 503, 504}


def _retry(fn, *args, attempts: int = 5, **kwargs):
    for attempt in range(1, attempts + 1):
        try:
            return fn(*args, **kwargs)
        except errors.APIError as exc:
            if exc.code not in RETRYABLE or attempt == attempts:
                raise
            delay = 2**attempt
            log.warning("Gemini API %s, retrying in %ss (%d/%d)", exc.code, delay, attempt, attempts)
            time.sleep(delay)


def _metadata(doc: types.Document) -> dict[str, str]:
    return {m.key: m.string_value for m in (doc.custom_metadata or []) if m.string_value is not None}


class FileSearchStore:
    def __init__(self, api_key: str, display_name: str, max_tokens_per_chunk: int, max_overlap_tokens: int):
        self.client = genai.Client(api_key=api_key)
        self.display_name = display_name
        self.chunking = types.ChunkingConfig(
            white_space_config=types.WhiteSpaceConfig(
                max_tokens_per_chunk=max_tokens_per_chunk,
                max_overlap_tokens=max_overlap_tokens,
            )
        )
        self.name = self._get_or_create()

    def _get_or_create(self) -> str:
        for store in self.client.file_search_stores.list():
            if store.display_name == self.display_name:
                log.info("Using File Search store %s (%s)", store.name, self.display_name)
                return store.name
        store = self.client.file_search_stores.create(config={"display_name": self.display_name})
        log.info("Created File Search store %s (%s)", store.name, self.display_name)
        return store.name

    def list_documents(self) -> list[RemoteDoc]:
        docs = []
        for doc in self.client.file_search_stores.documents.list(parent=self.name, config={"page_size": 20}):
            meta = _metadata(doc)
            if "article_id" not in meta:
                log.warning("Ignoring document without article_id: %s", doc.name)
                continue
            docs.append(RemoteDoc(name=doc.name, article_id=meta["article_id"], content_hash=meta.get("content_hash", "")))
        return docs

    def upload(self, doc: LocalDoc, attempts: int = 3) -> None:
        """Upload and wait for indexing. A resumable upload can be dropped server-side
        ("Upload has already been terminated", HTTP 400), so the whole upload is retried."""
        for attempt in range(1, attempts + 1):
            try:
                return self._upload_once(doc)
            except (errors.APIError, RuntimeError) as exc:
                if attempt == attempts:
                    raise
                log.warning("Upload of %s failed (%s), retrying (%d/%d)", doc.article_id, exc, attempt, attempts)
                time.sleep(2**attempt)

    def _upload_once(self, doc: LocalDoc) -> None:
        op = _retry(
            self.client.file_search_stores.upload_to_file_search_store,
            file_search_store_name=self.name,
            file=str(doc.path),
            config=types.UploadToFileSearchStoreConfig(
                display_name=doc.title[:500],
                mime_type="text/markdown",
                chunking_config=self.chunking,
                custom_metadata=[
                    types.CustomMetadata(key="article_id", string_value=doc.article_id),
                    types.CustomMetadata(key="content_hash", string_value=doc.content_hash),
                    types.CustomMetadata(key="source_url", string_value=doc.url),
                    types.CustomMetadata(key="updated_at", string_value=doc.updated_at),
                ],
            ),
        )
        while not op.done:
            time.sleep(2)
            op = _retry(self.client.operations.get, op)
        if op.error:
            raise RuntimeError(f"Indexing failed for {doc.path.name}: {op.error}")

    def delete(self, doc: RemoteDoc) -> None:
        _retry(self.client.file_search_stores.documents.delete, name=doc.name, config={"force": True})
