import requests

from kbsync import scraper


class FlakySession:
    """First call drops mid-body, second call succeeds."""

    def __init__(self):
        self.calls = 0

    def get(self, url, timeout):
        self.calls += 1
        if self.calls == 1:
            raise requests.exceptions.ChunkedEncodingError("Connection broken: IncompleteRead")

        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return {"articles": [], "next_page": None}

        return Resp()


def test_get_json_retries_a_dropped_body(monkeypatch):
    monkeypatch.setattr(scraper.time, "sleep", lambda s: None)
    session = FlakySession()
    assert scraper._get_json(session, "https://x/api") == {"articles": [], "next_page": None}
    assert session.calls == 2
