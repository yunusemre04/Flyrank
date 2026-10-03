from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .routes.enrich import router as enrich_router

app = FastAPI(title="Week6 — Enrich API")
app.include_router(enrich_router)


@app.exception_handler(RequestValidationError)
async def on_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0]
    field = ".".join(str(part) for part in first_error["loc"] if part != "body")
    return JSONResponse(
        status_code=400,
        content={"detail": f"Invalid field '{field}': {first_error['msg']}"},
    )
