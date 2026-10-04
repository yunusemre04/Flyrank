import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import db, jobs, migrate
from .config import get_settings
from .errors import NotEmbedded
from .models import CostEntry, Image, ImageTag, Job, Post, Suggestion, utcnow
from .schemas import CheckRequest, PostCreate, ReviewRequest
from .services import ranking
from .services.ingest import ingest_directory, upsert_post
from .taxonomy import load_taxonomy

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = get_settings()
    if s.auto_migrate:
        migrate.upgrade(s.database_url)
    db.configure(s.database_url)
    with db.new_session() as session:
        jobs.mark_interrupted(session)
    yield


app = FastAPI(title="AI Image Understanding & Content Matching Engine", lifespan=lifespan)


def tax():
    return load_taxonomy(get_settings().taxonomy_path)


def _get(session: Session, model, pk: int, label: str):
    obj = session.get(model, pk)
    if obj is None:
        raise HTTPException(404, f"{label} {pk} not found")
    return obj


def image_dict(i: Image, with_tags: bool = False, session: Session | None = None) -> dict:
    d = {"id": i.id, "filename": i.filename, "status": i.status, "subject": i.subject, "category": i.category,
         "attributes": i.attributes, "caption": i.caption, "confidence": i.confidence, "flagged": i.flagged, "error": i.error, "attempts": i.attempts}
    return d


def job_dict(j: Job) -> dict:
    return {"id": j.id, "status": j.status, "total": j.total, "done": j.done, "failed": j.failed, "error": j.error,
            "progress": round((j.done + j.failed) / j.total, 3) if j.total else None}


def cand_dict(c: ranking.Candidate, sug: Suggestion | None) -> dict:
    return {"suggestion_id": sug.id if sug else None, "image_id": c.image.id, "filename": c.image.filename, "rank": c.rank,
            "similarity": round(c.similarity, 4), "subject": c.image.subject, "category": c.image.category,
            "confidence": c.image.confidence, "decision": "APPROVED" if c.decision.approved else "REJECTED",
            "codes": c.decision.codes, "reasons": c.decision.reasons, "review_status": sug.review_status if sug else None}


@app.get("/health")
def health():
    return {"status": "ok"}


# ---- images -----------------------------------------------------------------------------------
@app.post("/images/ingest")
def ingest(session: Session = Depends(db.get_session)):
    try:
        return ingest_directory(session, get_settings().image_dir)
    except FileNotFoundError as e:
        raise HTTPException(400, str(e))


@app.get("/images")
def list_images(status: str | None = None, flagged: bool | None = None, category: str | None = None,
                limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), session: Session = Depends(db.get_session)):
    q = select(Image).order_by(Image.id).limit(limit).offset(offset)
    if status:
        q = q.where(Image.status == status)
    if flagged is not None:
        q = q.where(Image.flagged == flagged)
    if category:
        q = q.where(Image.category == category.lower())
    return [image_dict(i) for i in session.scalars(q)]


@app.get("/images/{image_id}")
def get_image(image_id: int, session: Session = Depends(db.get_session)):
    img = _get(session, Image, image_id, "image")
    tags = session.execute(select(ImageTag.kind, ImageTag.value).where(ImageTag.image_id == image_id)).all()
    return {**image_dict(img), "tags": [{"kind": k, "value": v} for k, v in tags]}


# ---- posts ------------------------------------------------------------------------------------
@app.post("/posts", status_code=201)
def create_post(body: PostCreate, session: Session = Depends(db.get_session)):
    post, created = upsert_post(session, body.slug, body.title, body.body)
    return {"id": post.id, "slug": post.slug, "created": created}


@app.get("/posts")
def list_posts(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), session: Session = Depends(db.get_session)):
    return [{"id": p.id, "slug": p.slug, "title": p.title} for p in session.scalars(select(Post).order_by(Post.id).limit(limit).offset(offset))]


@app.get("/posts/{post_id}/images")
def post_images(post_id: int, top_k: int = Query(5, ge=1, le=50), session: Session = Depends(db.get_session)):
    """Ranked, guard-checked image suggestions. Upserts Suggestion rows so they can be reviewed."""
    post = _get(session, Post, post_id, "post")
    s = get_settings()
    try:
        res = ranking.rank_post(session, post, s, tax(), top_k)
    except NotEmbedded as e:
        raise HTTPException(409, str(e))
    sugs = ranking.persist(session, post, res.top)
    cands = [cand_dict(c, sugs[c.image.id]) for c in res.top]
    return {"post": {"id": post.id, "slug": post.slug, "title": post.title}, "post_subjects": sorted(res.post_subjects),
            "no_confident_match": res.no_confident_match, "reasons": res.reasons,
            "suggested": next((c for c in cands if c["decision"] == "APPROVED"), None), "candidates": cands,
            "thresholds": {"similarity": s.similarity_threshold, "confidence_min": s.confidence_min}}


@app.post("/posts/{post_id}/check")
def check(post_id: int, body: CheckRequest, session: Session = Depends(db.get_session)):
    """Force one image as the candidate and show whether the guard accepts it."""
    post = _get(session, Post, post_id, "post")
    _get(session, Image, body.image_id, "image")
    try:
        cand = ranking.check_candidate(session, post, body.image_id, get_settings(), tax())
    except NotEmbedded as e:
        raise HTTPException(409, str(e))
    if cand is None:
        raise HTTPException(409, "image has no embedding yet (not processed, or embedded with another model)")
    sugs = ranking.persist(session, post, [cand], prune=False)  # a forced check must not drop other suggestions
    return cand_dict(cand, sugs[cand.image.id]) | {"forced": True}


# ---- jobs -------------------------------------------------------------------------------------
@app.post("/jobs/process", status_code=202)
def start_job(session: Session = Depends(db.get_session)):
    job = jobs.create_job(session)
    if job is None:
        raise HTTPException(409, "a job is already queued or running")
    jobs.start_in_background(job.id)
    return job_dict(job)


@app.get("/jobs/{job_id}")
def get_job(job_id: int, session: Session = Depends(db.get_session)):
    return job_dict(_get(session, Job, job_id, "job"))


# ---- review -----------------------------------------------------------------------------------
@app.get("/suggestions")
def list_suggestions(post_id: int | None = None, review_status: str | None = None, limit: int = Query(50, ge=1, le=200),
                     offset: int = Query(0, ge=0), session: Session = Depends(db.get_session)):
    q = select(Suggestion).order_by(Suggestion.post_id, Suggestion.rank).limit(limit).offset(offset)
    if post_id:
        q = q.where(Suggestion.post_id == post_id)
    if review_status:
        q = q.where(Suggestion.review_status == review_status)
    return [{"id": x.id, "post_id": x.post_id, "image_id": x.image_id, "rank": x.rank, "similarity": round(x.similarity, 4),
             "guard_approved": x.guard_approved, "review_status": x.review_status} for x in session.scalars(q)]


@app.get("/suggestions/{sid}")
def inspect_suggestion(sid: int, session: Session = Depends(db.get_session)):
    """Why was this image selected or refused?"""
    x = _get(session, Suggestion, sid, "suggestion")
    post, img = session.get(Post, x.post_id), session.get(Image, x.image_id)
    return {"id": x.id, "post": {"id": post.id, "title": post.title}, "image": image_dict(img), "rank": x.rank,
            "similarity": round(x.similarity, 4), "guard": {"approved": x.guard_approved, "codes": x.codes, "reasons": x.reasons},
            "review": {"status": x.review_status, "note": x.review_note, "reviewed_at": x.reviewed_at}}


@app.post("/suggestions/{sid}/review")
def review(sid: int, body: ReviewRequest, session: Session = Depends(db.get_session)):
    x = _get(session, Suggestion, sid, "suggestion")
    if body.decision == "approve" and not x.guard_approved and not body.override:
        raise HTTPException(409, {"error": "guard refused this pairing; send override=true to approve anyway", "reasons": x.reasons})
    status = "approved" if body.decision == "approve" else "rejected"
    if x.review_status != status or x.review_note != body.note:  # repeating the same review is a no-op
        x.review_status, x.review_note, x.reviewed_at = status, body.note, utcnow()
        session.commit()
    return {"id": x.id, "review_status": x.review_status, "guard_approved": x.guard_approved}


# ---- costs ------------------------------------------------------------------------------------
@app.get("/costs")
def costs(job_id: int | None = None, session: Session = Depends(db.get_session)):
    q = select(CostEntry.kind, CostEntry.model, func.count(), func.sum(CostEntry.input_tokens), func.sum(CostEntry.output_tokens),
               func.sum(CostEntry.cost_usd)).group_by(CostEntry.kind, CostEntry.model)
    if job_id:
        q = q.where(CostEntry.job_id == job_id)
    rows = session.execute(q).all()
    by = [{"kind": k, "model": m, "calls": n, "input_tokens": int(i or 0), "output_tokens": int(o or 0), "cost_usd": round(float(c or 0), 6)} for k, m, n, i, o, c in rows]
    return {"total_calls": sum(r["calls"] for r in by), "total_cost_usd": round(sum(r["cost_usd"] for r in by), 6),
            "budget_usd": get_settings().budget_usd, "by_kind": by}


@app.get("/costs/entries")
def cost_entries(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0), session: Session = Depends(db.get_session)):
    q = select(CostEntry).order_by(CostEntry.id.desc()).limit(limit).offset(offset)
    return [{"id": c.id, "job_id": c.job_id, "kind": c.kind, "provider": c.provider, "model": c.model, "image_id": c.image_id,
             "post_id": c.post_id, "input_tokens": c.input_tokens, "output_tokens": c.output_tokens, "cost_usd": c.cost_usd, "ok": c.ok}
            for c in session.scalars(q)]
