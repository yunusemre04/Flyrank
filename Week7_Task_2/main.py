import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from db import get_conn, init_schema
from render import render_pdf
from report_data import get_report_data

REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="PDF report generator")
generate_lock = threading.Lock()  # makes check-then-generate atomic for rapid double POSTs


class CreateReport(BaseModel):
    force: bool = False


@app.on_event("startup")
def startup():
    conn = get_conn()
    init_schema(conn)
    conn.close()


def _payload(row):
    return {"id": row["id"], "created_at": row["created_at"], "file": f"/reports/{row['id']}/file"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reports")
def create_report(body: CreateReport | None = None):
    force = body.force if body else False
    today = datetime.now(timezone.utc).date().isoformat()
    generate_lock.acquire()
    conn = get_conn()
    try:
        # Stage 5: idempotency — reuse today's report unless force=true
        if not force:
            existing = conn.execute(
                "SELECT * FROM reports WHERE substr(created_at, 1, 10) = ? ORDER BY id DESC LIMIT 1",
                (today,),
            ).fetchone()
            if existing and Path(existing["path"]).exists():
                return JSONResponse(_payload(existing), status_code=200)

        # Stage 4: whole pipeline inside the request
        data = get_report_data()
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.execute("INSERT INTO reports (path, created_at) VALUES ('', ?)", (now,))
        report_id = cur.lastrowid
        path = REPORTS_DIR / f"{report_id}.pdf"
        try:
            render_pdf(data, path)
        except Exception:
            conn.rollback()
            raise
        conn.execute("UPDATE reports SET path = ? WHERE id = ?", (str(path), report_id))
        conn.commit()
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        return JSONResponse(_payload(row), status_code=201)
    finally:
        conn.close()
        generate_lock.release()


def _get_row(report_id: int):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return row


@app.get("/reports/{report_id}")
def get_report(report_id: int):
    return _payload(_get_row(report_id))


@app.get("/reports/{report_id}/file")
def get_report_file(report_id: int):
    row = _get_row(report_id)
    if not Path(row["path"]).exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(row["path"], media_type="application/pdf", filename=f"report-{report_id}.pdf")
