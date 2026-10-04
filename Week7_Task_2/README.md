# PDF report generator (FlyRank A8)

A small FastAPI service: **query → render → store → serve**. One SQL pass turns 200 orders into a few numbers, an HTML template becomes a PDF via headless Chromium (Playwright), the file is stored on disk, and the API hands it out by link.

**Dataset:** Option A, the little shop (200 seeded random orders).

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

python seed.py                      # creates report.db, safe to run twice
uvicorn main:app --port 8000        # start the API
```

Try it:

```bash
curl -i -X POST localhost:8000/reports              # 201 + link (after a few seconds)
curl localhost:8000/reports/1                       # the record
curl -o my-report.pdf localhost:8000/reports/1/file # download the PDF
curl -X POST localhost:8000/reports                 # same day -> 200, same id
curl -X POST localhost:8000/reports -H 'content-type: application/json' -d '{"force":true}'  # new report
```

Stage 2/3 helper: `python test_report.py` prints the aggregates as JSON and writes `reports/test.pdf`.

## Endpoints

| Method | Path | Result |
|---|---|---|
| GET | `/health` | `{"status":"ok"}` |
| POST | `/reports` | `201` new report, or `200` existing one from today. Body `{"force": true}` skips the check |
| GET | `/reports/{id}` | the record + file link, `404` if unknown |
| GET | `/reports/{id}/file` | the PDF from disk |

## Aggregation SQL

```sql
-- totals
SELECT COUNT(*) AS total_orders, ROUND(COALESCE(SUM(amount), 0), 2) AS total_revenue FROM orders;

-- top 5 products by revenue
SELECT product, COUNT(*) AS orders, ROUND(SUM(amount), 2) AS revenue
FROM orders GROUP BY product ORDER BY revenue DESC LIMIT 5;

-- orders per day, last 7 days
SELECT created_at AS day, COUNT(*) AS orders
FROM orders WHERE created_at >= date('now', '-6 days')
GROUP BY created_at ORDER BY created_at;
```

## POST → download proof

_Paste your terminal output here: the `time curl -i -X POST ...` result and `file my-report.pdf`._

Double-click proof (two rapid POSTs, same id, one new file):

_Paste output here._

## Screenshot

_Add a screenshot of page 1 of a generated PDF as `docs/page1.png` and link it here._

## Stage 4 — when would I move this out of the request?

_Write your own sentence. Draft: when generation takes more than a few seconds, when many users trigger it at once, or when the report grows (thousands of rows), because a long request can time out and ties up the user and a server worker._

## Stage 5 — idempotency

_Write your own two sentences. Draft: the check stops a double-click or retry from generating and storing two identical PDFs. Without it, a billing system could email an invoice twice or charge a customer twice, which costs money and trust._

## Design notes

- PDFs live in `reports/`, only their path is in the `reports` table. JSON never carries file bytes.
- `tr { break-inside: avoid }` plus a `<thead>` keeps rows whole and repeats the header on each page.
- A lock around check-then-generate makes simultaneous double POSTs safe, not just sequential ones.
