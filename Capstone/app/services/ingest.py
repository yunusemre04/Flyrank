import hashlib
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Image, Post, PostVector

EXT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
MAX_BYTES = 10 * 1024 * 1024


def ingest_directory(session: Session, directory: str) -> dict:
    d = Path(directory)
    if not d.is_dir():
        raise FileNotFoundError(f"image directory not found: {directory}")
    added = skipped = rejected = 0
    for p in sorted(d.iterdir()):
        mime = EXT.get(p.suffix.lower())
        if not mime:
            continue
        data = p.read_bytes()
        if len(data) > MAX_BYTES:
            rejected += 1
            continue
        sha = hashlib.sha256(data).hexdigest()
        if session.scalar(select(Image.id).where((Image.sha256 == sha) | (Image.filename == p.name))):
            skipped += 1  # idempotent: re-ingesting never duplicates
            continue
        session.add(Image(filename=p.name, path=str(p.resolve()), sha256=sha, mime=mime))
        added += 1
    session.commit()
    return {"added": added, "skipped": skipped, "rejected_too_large": rejected}


def upsert_post(session: Session, slug: str, title: str, body: str) -> tuple[Post, bool]:
    """Returns (post, created). Changed text drops the old embedding so the next job refreshes it."""
    post = session.scalar(select(Post).where(Post.slug == slug))
    if post is None:
        post = Post(slug=slug, title=title, body=body)
        session.add(post)
        session.commit()
        return post, True
    if (post.title, post.body) != (title, body):
        post.title, post.body = title, body
        old = session.get(PostVector, post.id)
        if old:
            session.delete(old)
        session.commit()
    return post, False
