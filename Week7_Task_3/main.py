"""A7 - Your first background job (Python lane: FastAPI + Inngest)."""
import datetime
import uuid

import inngest
import inngest.fast_api
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="Report API")

# In-memory store: forgets everything on restart (same lesson as A1).
reports: dict[str, dict] = {}

inngest_client = inngest.Inngest(
    app_id="report-api",
    is_production=False,  # talk to the local Dev Server, no keys needed
)


# ---------------------------------------------------------------- Stage 0
@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------- Stage 2/3
@app.post("/reports", status_code=202)
async def create_report(body: dict | None = None):
    topic = (body or {}).get("topic")
    # Stage 3: wrong input is rejected at the door - no event, no job, no retry.
    if not isinstance(topic, str) or not topic.strip():
        return JSONResponse({"error": "topic is required"}, status_code=400)

    report_id = str(uuid.uuid4())
    reports[report_id] = {"id": report_id, "topic": topic, "status": "pending"}

    await inngest_client.send(
        inngest.Event(
            name="report/requested",
            data={"id": report_id, "topic": topic},
        )
    )
    # No slow work here - that is the whole point.
    return {"id": report_id, "status": "pending"}


@app.get("/reports/{report_id}")
async def get_report(report_id: str):
    report = reports.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    return report


# ---------------------------------------------------------------- Stage 1
@inngest_client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context) -> str:
    await ctx.step.sleep("wait-a-bit", datetime.timedelta(seconds=5))
    return "Hello from the background!"


# ---------------------------------------------------------------- Stage 2/3
async def _mark_failed(ctx: inngest.Context) -> None:
    """Runs once all retries are used up -> the report becomes 'failed'."""
    original = ctx.event.data.get("event", {}).get("data", {})
    report = reports.get(original.get("id", ""))
    if report is not None:
        report["status"] = "failed"


@inngest_client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
    retries=2,  # 1 first attempt + 2 retries = 3 attempts
    on_failure=_mark_failed,
    # Stretch (concurrency limit): uncomment to run at most 2 reports at once
    # concurrency=[inngest.Concurrency(limit=2)],
)
async def make_report(ctx: inngest.Context) -> dict:
    report_id = ctx.event.data["id"]
    topic = ctx.event.data["topic"]

    # Stand-in for a real slow task (an AI call, a big export).
    await ctx.step.sleep("do-the-slow-work", datetime.timedelta(seconds=8))

    async def build_report() -> dict:
        if topic == "fail":
            raise Exception("The report oven is broken!")
        report = reports.get(report_id)
        # Stretch (idempotency): a duplicate event must not rebuild the report.
        if report is not None and report["status"] == "done":
            return report
        result = f"Report about {topic}: {topic.title()} are wonderful. (built in the background)"
        done = {"id": report_id, "topic": topic, "status": "done", "result": result}
        reports[report_id] = done
        return done

    return await ctx.step.run("build-report", build_report)


# ---------------------------------------------------------------- Stage 4
@inngest_client.create_function(
    fn_id="heartbeat",
    trigger=inngest.TriggerCron(cron="* * * * *"),  # every minute (testing only)
)
async def heartbeat(ctx: inngest.Context) -> dict:
    counts = {"pending": 0, "done": 0, "failed": 0}
    for r in reports.values():
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    ctx.logger.info(
        f"heartbeat: pending={counts['pending']} done={counts['done']} failed={counts['failed']}"
    )
    return counts


# Serve all functions at /api/inngest
inngest.fast_api.serve(app, inngest_client, [say_hello, make_report, heartbeat])
