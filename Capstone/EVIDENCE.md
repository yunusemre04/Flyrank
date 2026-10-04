# EVIDENCE

One pasted proof per Section 6 requirement. **Fill each slot with real output from YOUR run (Gemini or Ollama)**;
claims without evidence score as not done. Do not paste `PROVIDER=mock` output here.

| # | Requirement | Command to produce proof | Proof |
|---|---|---|---|
| 1 | Vision output schema-validated; invalid never trusted | `pytest tests/test_schema_and_guard.py -k tags -v` + one `GET /images/{id}` | _paste_ |
| 2 | Low-confidence flagged, not accepted | `curl 'localhost:8000/images?flagged=true'` | _paste_ |
| 3 | Batch background job with retries | `curl -X POST localhost:8000/jobs/process` then `GET /jobs/{id}`; `pytest -k flaky -v` | _paste_ |
| 4 | Costs tracked per call | `curl localhost:8000/costs` and `/costs/entries` | _paste_ |
| 5 | Embeddings stored; posts return ranked images | `curl localhost:8000/posts/1/images` | _paste_ |
| 6 | "red fox" ~ "Vulpes vulpes" | `curl localhost:8000/posts/2/images` | _paste_ |
| 7 | Wolf on fox post provably fails | `curl -X POST localhost:8000/posts/1/check -d '{"image_id": <wolf id>}' -H 'content-type: application/json'` | _paste_ |
| 8 | Rejections explain themselves | same output as #7 (`reasons`) | _paste_ |
| 9 | "No confident match" + reasons | `curl localhost:8000/posts/<snow-leopard id>/images` | _paste_ |
| 10 | Models/indexes/migrations | `alembic upgrade head` output; `\d suggestions` in psql | _paste_ |
| 11 | Validated endpoints + review workflow | `pytest tests/test_api.py -v` | _paste_ |
| 12 | Top-1 precision measured, matches README | `python -m scripts.eval --write-readme` | _paste_ |
| 13 | README + diagram + required files | `ls` | _paste_ |
