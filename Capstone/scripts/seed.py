"""Seed demo data: ingest images, load posts, run the batch job to completion (synchronously)."""
import json

from app import db, jobs, migrate
from app.config import get_settings
from app.models import Job
from app.services.ingest import ingest_directory, upsert_post


def main() -> None:
    s = get_settings()
    migrate.upgrade(s.database_url)
    db.configure(s.database_url)
    with db.new_session() as session:
        print("ingest:", ingest_directory(session, s.image_dir))
        for p in json.load(open(s.posts_path, encoding="utf-8")):
            upsert_post(session, p["slug"], p["title"], p["body"])
        job = jobs.create_job(session)
        if job is None:
            raise SystemExit("a job is already queued or running")
        job_id = job.id
    jobs.run_job(job_id, s)
    with db.new_session() as session:
        j = session.get(Job, job_id)
        print(f"job {j.id}: {j.status} done={j.done} failed={j.failed} total={j.total} {j.error or ''}")


if __name__ == "__main__":
    main()
