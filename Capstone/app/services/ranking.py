from dataclasses import dataclass, field

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import NotEmbedded
from ..models import IMAGE_READY, Image, ImageVector, Post, PostVector, Suggestion
from . import guard


@dataclass
class Candidate:
    image: Image
    similarity: float
    rank: int
    decision: guard.Decision


@dataclass
class RankResult:
    post: Post
    post_subjects: dict
    ranked: list[Candidate]  # every image, best first (guard verdict attached to each)
    top: list[Candidate]  # the top_k shown to the caller
    best: Candidate | None  # highest-ranked candidate the guard approved
    reasons: list[str] = field(default_factory=list)  # why there is no confident match

    @property
    def no_confident_match(self) -> bool:
        return self.best is None


def _scored(session: Session, post: Post) -> list[tuple[Image, float]]:
    pv = session.get(PostVector, post.id)
    if pv is None:
        raise NotEmbedded(f"post '{post.slug}' has no embedding yet; run POST /jobs/process")
    rows = session.execute(
        select(Image, ImageVector).join(ImageVector, ImageVector.image_id == Image.id)
        .where(Image.status.in_(IMAGE_READY), ImageVector.model == pv.model)  # never compare across embedding models
    ).all()
    if not rows:
        return []
    mat = np.array([v.vector for _, v in rows], dtype=float)
    q = np.array(pv.vector, dtype=float)
    sims = mat @ q / (np.linalg.norm(mat, axis=1) * np.linalg.norm(q) + 1e-12)
    order = np.argsort(-sims)
    return [(rows[i][0], float(sims[i])) for i in order]


def _judge(post: Post, img: Image, sim: float, subjects: dict, tax, settings) -> guard.Decision:
    return guard.evaluate(similarity=sim, confidence=img.confidence, flagged=img.flagged, image_subject=img.subject,
                          image_category=img.category, image_caption=img.caption, post_subjects=subjects, tax=tax, settings=settings)


def rank_post(session: Session, post: Post, settings, tax, top_k: int | None = None) -> RankResult:
    subjects = tax.post_subjects(post.title, post.body)
    ranked = [Candidate(img, sim, i + 1, _judge(post, img, sim, subjects, tax, settings))
              for i, (img, sim) in enumerate(_scored(session, post))]
    top = ranked[: top_k or settings.top_k]
    best = next((c for c in ranked if c.decision.approved), None)
    reasons: list[str] = []
    if best is None:
        if not ranked:
            reasons.append("No processed images are available")
        else:
            head = ranked[0]
            reasons.append(f"Best candidate '{head.image.filename}' (similarity {head.similarity:.2f}) was refused")
            reasons += list(dict.fromkeys(head.decision.reasons))
    return RankResult(post, subjects, ranked, top, best, reasons)


def check_candidate(session: Session, post: Post, image_id: int, settings, tax) -> Candidate | None:
    """Force a specific image as a candidate (e.g. the wolf on the fox post) and run the guard on it."""
    res = rank_post(session, post, settings, tax)
    return next((c for c in res.ranked if c.image.id == image_id), None)


def persist(session: Session, post: Post, candidates: list[Candidate], prune: bool = True) -> dict[int, Suggestion]:
    """Idempotent upsert: re-ranking never duplicates rows and never wipes a human review."""
    existing = {s.image_id: s for s in session.scalars(select(Suggestion).where(Suggestion.post_id == post.id))}
    keep = {c.image.id for c in candidates}
    for iid, s in list(existing.items()):
        if prune and iid not in keep and s.review_status == "pending":
            session.delete(s)
            del existing[iid]
    for c in candidates:
        s = existing.get(c.image.id)
        if s is None:
            s = existing[c.image.id] = Suggestion(post_id=post.id, image_id=c.image.id)
            session.add(s)
        s.rank, s.similarity = c.rank, c.similarity
        s.guard_approved, s.codes, s.reasons = c.decision.approved, c.decision.codes, c.decision.reasons
    session.commit()
    return existing
