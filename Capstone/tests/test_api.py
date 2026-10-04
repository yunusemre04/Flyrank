import json
import time

from app.config import get_settings


def _load(client):
    assert client.post("/images/ingest").json()["added"] == 46
    for p in json.load(open(get_settings().posts_path)):
        assert client.post("/posts", json=p).status_code == 201
    r = client.post("/jobs/process")
    assert r.status_code == 202
    jid = r.json()["id"]
    for _ in range(200):
        j = client.get(f"/jobs/{jid}").json()
        if j["status"] not in ("queued", "running"):
            return j
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_full_flow_over_http(client):
    j = _load(client)
    assert j["status"] == "succeeded" and j["progress"] == 1.0
    assert client.post("/jobs/process").status_code == 202  # nothing left to do, but allowed once the first has finished
    posts = {p["slug"]: p["id"] for p in client.get("/posts?limit=200").json()}

    body = client.get(f"/posts/{posts['red-fox-behavior']}/images").json()
    assert body["suggested"]["filename"].startswith("red-fox_") and not body["no_confident_match"]
    assert body["candidates"][0]["decision"] == "APPROVED"

    none = client.get(f"/posts/{posts['volcano-hiking-guide']}/images").json()
    assert none["no_confident_match"] and none["suggested"] is None and none["reasons"]

    wolf = next(i for i in client.get("/images?limit=200").json() if i["filename"] == "gray-wolf_01.jpg")
    chk = client.post(f"/posts/{posts['red-fox-behavior']}/check", json={"image_id": wolf["id"]}).json()
    assert chk["decision"] == "REJECTED" and "expected red fox, detected gray wolf" in " ".join(chk["reasons"])

    # review: approving a guard-refused pairing needs an explicit override
    sid = chk["suggestion_id"]
    r = client.post(f"/suggestions/{sid}/review", json={"decision": "approve"})
    assert r.status_code == 409 and r.json()["detail"]["reasons"]
    assert client.post(f"/suggestions/{sid}/review", json={"decision": "reject", "note": "wolf"}).json()["review_status"] == "rejected"
    assert client.get(f"/suggestions/{sid}").json()["guard"]["approved"] is False

    # re-ranking keeps the human review (idempotent upsert)
    client.get(f"/posts/{posts['red-fox-behavior']}/images?top_k=50")
    assert client.get(f"/suggestions/{sid}").json()["review"]["status"] == "rejected"

    good = body["suggested"]["suggestion_id"]
    assert client.post(f"/suggestions/{good}/review", json={"decision": "approve"}).json()["review_status"] == "approved"

    costs = client.get("/costs").json()
    assert costs["total_calls"] >= 46 * 2 + 17 and costs["by_kind"]
    flagged = client.get("/images?flagged=true").json()
    assert [i["filename"] for i in flagged] == ["blurry_01.jpg"]


def test_validation_and_errors_are_clean_4xx(client):
    assert client.post("/posts", json={"slug": "Bad Slug", "title": "x", "body": ""}).status_code == 422
    assert client.post("/posts", json={"slug": "ok-slug"}).status_code == 422
    assert client.get("/posts/999/images").status_code == 404
    assert client.get("/images/999").status_code == 404
    assert client.get("/jobs/999").status_code == 404
    assert client.get("/images?limit=0").status_code == 422
    p = client.post("/posts", json={"slug": "no-vec", "title": "No vector yet", "body": "fox"}).json()
    assert client.get(f"/posts/{p['id']}/images").status_code == 409  # not embedded yet
    assert client.post(f"/posts/{p['id']}/check", json={"image_id": 0}).status_code == 422
    assert client.post("/suggestions/999/review", json={"decision": "maybe"}).status_code == 422


def test_post_upsert_is_idempotent(client):
    a = client.post("/posts", json={"slug": "same", "title": "Same title", "body": "body"}).json()
    b = client.post("/posts", json={"slug": "same", "title": "Same title", "body": "body"}).json()
    assert a["id"] == b["id"] and b["created"] is False
