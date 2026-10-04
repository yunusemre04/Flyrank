import dataclasses
import json
from pathlib import Path

from sqlalchemy import func, select

from app import db, jobs
from app.config import get_settings
from app.models import CostEntry, Image, Job, Post, PostVector
from app.services import ranking
from app.taxonomy import load_taxonomy
from scripts.eval import evaluate
from tests.conftest import make_image


def _post(session, slug):
    return session.scalar(select(Post).where(Post.slug == slug))


def test_job_tags_everything_and_flags_low_confidence(seeded):
    with db.new_session() as s:
        j = s.get(Job, seeded)
        assert j.status == "succeeded" and j.failed == 0 and j.done == j.total == 46 + 17
        statuses = {i.filename: i.status for i in s.scalars(select(Image))}
        assert statuses["blurry_01.jpg"] == "flagged"
        assert sum(1 for v in statuses.values() if v == "tagged") == 45
        assert all(i.subject and i.caption and 0 <= i.confidence <= 1 for i in s.scalars(select(Image)))


def test_fox_post_ranks_fox_first_and_wolf_lower(seeded):
    s_, tax = get_settings(), load_taxonomy(get_settings().taxonomy_path)
    with db.new_session() as s:
        res = ranking.rank_post(s, _post(s, "red-fox-behavior"), s_, tax)
        assert res.best.image.filename.startswith("red-fox_")
        assert res.ranked[0].image.filename.startswith("red-fox_")
        sims = {c.image.filename: c.similarity for c in res.ranked}
        assert sims["red-fox_01.jpg"] > sims["gray-wolf_01.jpg"] + 0.3 and sims["red-fox_01.jpg"] > sims["dog_01.jpg"] + 0.3


def test_synonym_post_matches_fox(seeded):
    s_, tax = get_settings(), load_taxonomy(get_settings().taxonomy_path)
    with db.new_session() as s:
        res = ranking.rank_post(s, _post(s, "vulpes-field-notes"), s_, tax)
        assert res.best.image.filename.startswith("red-fox_")


def test_forced_wolf_is_rejected(seeded):
    s_, tax = get_settings(), load_taxonomy(get_settings().taxonomy_path)
    with db.new_session() as s:
        wolf = s.scalar(select(Image).where(Image.filename == "gray-wolf_01.jpg"))
        cand = ranking.check_candidate(s, _post(s, "red-fox-behavior"), wolf.id, s_, tax)
        assert not cand.decision.approved and any("expected red fox, detected gray wolf" in r for r in cand.decision.reasons)


def test_no_confident_match_for_post_without_image(seeded):
    s_, tax = get_settings(), load_taxonomy(get_settings().taxonomy_path)
    with db.new_session() as s:
        res = ranking.rank_post(s, _post(s, "snow-leopard-conservation"), s_, tax)
        assert res.no_confident_match and res.reasons and any("threshold" in r for r in res.reasons)


def test_eval_set_precision(seeded):
    s_ = get_settings()
    with db.new_session() as s:
        r = evaluate(s, s_, load_taxonomy(s_.taxonomy_path), json.load(open(s_.eval_path)))
    assert r["top1_precision"] == 1.0 and r["wrong_suggestions"] == 0 and r["abstention_on_negatives"] == "2/2"


def test_every_call_has_a_cost_entry(seeded):
    with db.new_session() as s:
        n = s.scalar(select(func.count()).select_from(CostEntry))
        assert n == 46 + 46 + 17  # vision + image embeddings + post embeddings
        assert s.scalar(select(func.count()).select_from(CostEntry).where(CostEntry.job_id.is_(None))) == 0


def test_rerun_is_idempotent(seeded):
    s_ = get_settings()
    with db.new_session() as s:
        before = s.scalar(select(func.count()).select_from(CostEntry))
        job = jobs.create_job(s)
    jobs.run_job(job.id, s_)
    with db.new_session() as s:
        assert s.scalar(select(func.count()).select_from(CostEntry)) == before  # nothing re-processed, nothing re-billed
        assert s.get(Job, job.id).total == 0


def test_only_one_active_job(env):
    with db.new_session() as s:
        assert jobs.create_job(s) is not None
        assert jobs.create_job(s) is None


def test_flaky_image_succeeds_after_retries_and_garbage_fails_without_blocking_others(env):
    from app.services.ingest import ingest_directory
    s_ = get_settings()
    make_image(env / "pizza-flaky_01.jpg")
    make_image(env / "garbage_01.jpg")
    with db.new_session() as s:
        ingest_directory(s, str(env))
        jid = jobs.create_job(s).id
    jobs.run_job(jid, s_)
    with db.new_session() as s:
        rows = {i.filename: i for i in s.scalars(select(Image))}
        assert rows["pizza-flaky_01.jpg"].status == "tagged"
        assert rows["garbage_01.jpg"].status == "failed" and "invalid" in rows["garbage_01.jpg"].error
        j = s.get(Job, jid)
        assert j.status == "partial" and j.failed == 1
        bad = s.scalars(select(CostEntry).where(CostEntry.image_id == rows["garbage_01.jpg"].id, CostEntry.kind == "vision")).all()
        assert len(bad) == s_.max_attempts and not any(c.ok for c in bad)  # every invalid attempt is still costed


def test_budget_guard_stops_the_job(env, monkeypatch):
    from app.services.ingest import ingest_directory
    monkeypatch.setenv("BUDGET_USD", "0")
    with db.new_session() as s:
        ingest_directory(s, str(env))
        jid = jobs.create_job(s).id
    jobs.run_job(jid, get_settings())
    with db.new_session() as s:
        assert s.get(Job, jid).status == "budget_exceeded"
        assert s.scalar(select(func.count()).select_from(Image).where(Image.status == "pending")) == 46  # resumable
