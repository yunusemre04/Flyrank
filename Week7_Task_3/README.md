# Report API — my first background job

A small FastAPI service whose slow work (an 8-second "report") runs in an
**Inngest background function**. The endpoint answers instantly with `202`,
a status endpoint reports progress, and a cron function runs on the clock alone.

Pattern: **accept fast → work in the background → report status.**

## Run it (two terminals)

```bash
python -m venv .venv && source .venv/bin/activate    # first time only
pip install -r requirements.txt                      # first time only

# Terminal 1 - the API
INNGEST_DEV=1 uvicorn main:app --port 8000

# Terminal 2 - the Inngest Dev Server (dashboard at http://localhost:8288)
npx inngest-cli@latest dev -u http://localhost:8000/api/inngest
```

## Endpoints and functions

| Name | Kind | Trigger | What it does |
|---|---|---|---|
| `GET /health` | endpoint | request | `{"status":"ok"}` |
| `POST /reports` | endpoint | request | validates `topic` (400 if missing), saves `pending`, sends `report/requested`, returns **202** + id |
| `GET /reports/{id}` | endpoint | request | status: `pending` → `done` (+ result) / `failed`; unknown id → 404 |
| `say-hello` | function | event `test/hello` | sleeps 5 s, returns a greeting (Stage 1) |
| `make-report` | function | event `report/requested` | step `do-the-slow-work` (sleep 8 s) → step `build-report`; `retries=2` |
| `heartbeat` | function | cron `* * * * *` | logs how many reports are pending / done / failed |

## Proof

```text
$ time curl -i -X POST http://localhost:8000/reports -H "Content-Type: application/json" -d '{"topic":"cats"}'
HTTP/1.1 202 Accepted
{"id":"<paste id>","status":"pending"}
real 0m0.0xxs

$ curl http://localhost:8000/reports/<id>        # right away
{"id":"...","topic":"cats","status":"pending"}

$ curl http://localhost:8000/reports/<id>        # ~10 seconds later
{"id":"...","topic":"cats","status":"done","result":"Report about cats: ..."}
```
<!-- Replace with YOUR real output. -->

## Stage 3 — retry vs. validation

<!-- Write your own sentence: a missing topic is wrong *input* (reject with 400 at the door, retrying can never fix it), while a failing job is a wrong *moment* (network/service hiccup) that a retry with backoff may fix. -->

## Stage 4 — cron

- Every day at 08:00: `...` <!-- build it on crontab.guru -->
- Every Sunday at 22:00: `...`


