import json
import zlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image as PILImage

ROOT = Path(__file__).resolve().parent.parent


def make_image(path: Path) -> None:
    c = zlib.crc32(path.name.encode())
    img = PILImage.new("RGB", (16, 16), ((c >> 16) & 255, (c >> 8) & 255, c & 255))
    img.putpixel((0, 0), (c % 251, 7, 9))
    img.save(path)


def corpus_names(extra=()):
    tax = json.load(open(ROOT / "data" / "taxonomy.json"))["subjects"]
    names = [f"{s['name'].replace(' ', '-')}_{i:02d}.jpg" for s in tax for i in (1, 2, 3)]
    return names + ["blurry_01.jpg", *extra]


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Isolated sqlite DB + fake image corpus named by convention, mock provider, no network."""
    imgs = tmp_path / "images"
    imgs.mkdir()
    for n in corpus_names():
        make_image(imgs / n)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 't.db'}")
    monkeypatch.setenv("IMAGE_DIR", str(imgs))
    monkeypatch.setenv("PROVIDER", "mock")
    monkeypatch.setenv("RETRY_BASE_DELAY", "0")
    monkeypatch.setenv("REQUEST_DELAY", "0")
    from app import db, migrate
    from app.config import get_settings
    s = get_settings()
    migrate.upgrade(s.database_url)
    db.configure(s.database_url)
    return imgs


@pytest.fixture
def seeded(env):
    """Everything ingested + the batch job run to completion."""
    from app import db, jobs
    from app.config import get_settings
    from app.services.ingest import ingest_directory, upsert_post
    s = get_settings()
    with db.new_session() as session:
        ingest_directory(session, s.image_dir)
        for p in json.load(open(s.posts_path)):
            upsert_post(session, p["slug"], p["title"], p["body"])
        job_id = jobs.create_job(session).id
    jobs.run_job(job_id, s)
    return job_id


@pytest.fixture
def client(env):
    from app.main import app
    with TestClient(app) as c:
        yield c
