from pathlib import Path

from kbsync.sync import LocalDoc, RemoteDoc, estimate_chunks, plan_sync


def local(article_id, h):
    return LocalDoc(article_id, "t", "u", "d", Path(f"{article_id}.md"), h)


def remote(article_id, h, name=None):
    return RemoteDoc(name or f"doc-{article_id}-{h}", article_id, h)


def test_plan_classifies_added_updated_skipped_removed():
    plan = plan_sync(
        local=[local("1", "a"), local("2", "b-new"), local("3", "c")],
        remote=[remote("2", "b-old"), remote("3", "c"), remote("9", "gone")],
        prune=True,
    )
    assert [d.article_id for d in plan.to_add] == ["1"]
    assert [(d.article_id, [r.content_hash for r in old]) for d, old in plan.to_update] == [("2", ["b-old"])]
    assert [d.article_id for d in plan.unchanged] == ["3"]
    assert [r.article_id for r in plan.to_remove] == ["9"]


def test_partial_scrape_never_removes():
    plan = plan_sync(local=[local("1", "a")], remote=[remote("9", "x")], prune=False)
    assert plan.to_remove == []


def test_duplicates_are_replaced_even_if_hash_matches():
    plan = plan_sync(local=[local("1", "a")], remote=[remote("1", "a", "d1"), remote("1", "a", "d2")], prune=True)
    assert len(plan.to_update) == 1 and len(plan.to_update[0][1]) == 2


def test_estimate_chunks():
    assert estimate_chunks("word " * 10, 400, 60) == 1
    assert estimate_chunks("word " * 400, 400, 60) == 1
    assert estimate_chunks("word " * 401, 400, 60) == 2
    assert estimate_chunks("word " * 1080, 400, 60) == 3
