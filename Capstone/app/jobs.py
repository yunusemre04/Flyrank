"""Batch background job: vision -> validate -> embed, with retries, progress, cost tracking and a budget guard."""
import logging
import threading
import time
from pathlib import Path

from sqlalchemy import select

from . import db
from .config import get_settings
from .errors import BudgetExceeded, InvalidModelOutput, ProviderError
from .models import IMAGE_READY, Image, ImageTag, ImageVector, Job, Post, PostVector, utcnow
from .providers import build_provider
from .schemas import ImageTags
from .services import embeddings, vision
from .services.costs import CostRecorder
from .taxonomy import load_taxonomy

log = logging.getLogger("app.jobs")
ACTIVE = ("queued", "running")


def create_job(session) -> Job | None:
    """One active job at a time: a retried/duplicated request must not run the work twice."""
    if session.scalar(select(Job.id).where(Job.status.in_(ACTIVE))):
        return None
    job = Job(kind="process", status="queued")
    session.add(job)
    session.commit()
    return job


def start_in_background(job_id: int) -> None:
    threading.Thread(target=run_job, args=(job_id,), daemon=True, name=f"job-{job_id}").start()


def mark_interrupted(session) -> None:
    for j in session.scalars(select(Job).where(Job.status.in_(ACTIVE))):
        j.status, j.error, j.finished_at = "failed", "interrupted by restart", utcnow()
    session.commit()


def _tags_from_row(img: Image) -> ImageTags | None:
    """Reuse tags saved by an earlier run so a failed embedding never re-pays for vision."""
    if img.caption and img.subject and img.category and img.confidence is not None:
        return ImageTags(subject=img.subject, category=img.category, attributes=img.attributes or [], caption=img.caption, confidence=img.confidence)
    return None


def _save_tags(s, img: Image, tags: ImageTags, settings) -> None:
    img.subject, img.category, img.attributes = tags.subject, tags.category, tags.attributes
    img.caption, img.confidence = tags.caption, tags.confidence
    img.flagged = tags.confidence < settings.confidence_min
    img.status = "flagged" if img.flagged else "tagged"
    for t in s.scalars(select(ImageTag).where(ImageTag.image_id == img.id)):
        s.delete(t)
    s.add(ImageTag(image_id=img.id, kind="subject", value=tags.subject[:80]))
    s.add(ImageTag(image_id=img.id, kind="category", value=tags.category[:40]))
    for a in tags.attributes:
        s.add(ImageTag(image_id=img.id, kind="attribute", value=a[:80]))
    s.commit()


def _upsert_vector(s, model_cls, key: str, key_val: int, provider, vec: list[float]) -> None:
    row = s.get(model_cls, key_val)
    if row is None:
        s.add(model_cls(**{key: key_val}, model=provider.embed_model, dim=len(vec), vector=vec))
    else:
        row.model, row.dim, row.vector = provider.embed_model, len(vec), vec
    s.commit()


def _process_image(s, provider, tax, settings, rec, job: Job, img: Image) -> None:
    img.status, img.error, img.attempts = "processing", None, img.attempts + 1
    s.commit()
    try:
        tags = _tags_from_row(img)
        if tags is None:
            tags = vision.tag_image(provider, Path(img.path).read_bytes(), img.mime, img.filename, tax, settings, rec, img.id)
            _save_tags(s, img, tags, settings)
        else:
            img.status = "flagged" if img.flagged else "tagged"
            s.commit()
        vec = embeddings.embed_text(provider, embeddings.image_text(tags), settings, rec, image_id=img.id)
        _upsert_vector(s, ImageVector, "image_id", img.id, provider, vec)
        job.done += 1
    except BudgetExceeded:
        img.status = "pending" if not img.caption else img.status  # resumable once budget is raised
        s.commit()
        raise
    except (ProviderError, InvalidModelOutput, OSError) as e:
        img.status, img.error = "failed", f"{type(e).__name__}: {e}"[:500]
        job.failed += 1
        log.error("ALERT job=%s image=%s failed after retries: %s", job.id, img.filename, img.error)
    s.commit()


def _process_post(s, provider, settings, rec, job: Job, post: Post) -> None:
    try:
        vec = embeddings.embed_text(provider, embeddings.post_text(post.title, post.body), settings, rec, post_id=post.id)
        _upsert_vector(s, PostVector, "post_id", post.id, provider, vec)
        job.done += 1
    except (ProviderError, InvalidModelOutput) as e:
        job.failed += 1
        log.error("ALERT job=%s post=%s embedding failed: %s", job.id, post.slug, e)
    s.commit()


def run_job(job_id: int, settings=None, provider=None) -> None:
    settings = settings or get_settings()
    tax = load_taxonomy(settings.taxonomy_path)
    with db.new_session() as s:
        job = s.get(Job, job_id)
        job.status = "running"
        s.commit()
        try:
            provider = provider or build_provider(settings)
        except ProviderError as e:
            job.status, job.error, job.finished_at = "failed", str(e), utcnow()
            s.commit()
            log.error("ALERT job=%s cannot start: %s", job_id, e)
            return
        images = list(s.scalars(select(Image).where(Image.status.in_(("pending", "failed"))).order_by(Image.id)))
        posts = list(s.scalars(select(Post).outerjoin(PostVector).where(PostVector.post_id.is_(None)).order_by(Post.id)))
        job.total = len(images) + len(posts)
        s.commit()
        rec = CostRecorder(s, settings, provider, job_id)
        try:
            for img in images:
                _process_image(s, provider, tax, settings, rec, job, img)
                time.sleep(settings.request_delay)
            for post in posts:
                _process_post(s, provider, settings, rec, job, post)
                time.sleep(settings.request_delay)
            job.status = "partial" if job.failed else "succeeded"
        except BudgetExceeded as e:
            job.status, job.error = "budget_exceeded", str(e)
            log.error("ALERT job=%s stopped: %s", job_id, e)
        except Exception as e:  # never leave a job stuck in 'running'
            job.status, job.error = "failed", f"{type(e).__name__}: {e}"[:500]
            log.exception("ALERT job=%s crashed", job_id)
        job.finished_at = utcnow()
        s.commit()
