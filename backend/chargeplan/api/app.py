"""HTTP API: a thin layer over the engine. No planning logic lives here.

    uvicorn chargeplan.api.app:app --reload        (from backend/)

    GET  /api/health                 is the server up?
    GET  /api/examples               bundled synthetic examples: [{key, title}]
    GET  /api/examples/{key}         one example's inputs, in the POST /api/plan shape
    POST /api/plan                   inputs -> full result (status, schedule, costs, explanation)

Stateless: nothing is stored. Interactive docs are served at /docs.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from ..engine import run_plan
from ..scenarios import SCENARIOS
from .schemas import PlanRequest

MAX_BODY_BYTES = 64_000  # a 10-van plan is about 3 KB
SOLVE_TIME_LIMIT_S = 5.0

app = FastAPI(title="ChargePlan API", version="0.2.0")


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    length = request.headers.get("content-length", "0")
    if not length.isdigit():
        return JSONResponse({"detail": "Bad Content-Length header."}, status_code=400)
    if int(length) > MAX_BODY_BYTES:
        return JSONResponse({"detail": "Request too large."}, status_code=413)
    return await call_next(request)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/examples")
def examples() -> list[dict]:
    return [{"key": s.key, "title": s.title} for s in SCENARIOS.values()]


@app.get("/api/examples/{key}")
def example(key: str) -> PlanRequest:
    if key not in SCENARIOS:
        raise HTTPException(status_code=404, detail="No example with that name.")
    return PlanRequest.from_engine(SCENARIOS[key].build())


@app.post("/api/plan")
def plan(request: PlanRequest) -> dict:
    # A plain `def` endpoint: FastAPI runs it in a worker thread, so a solve
    # never blocks other requests.
    return run_plan(request.to_engine(), time_limit_s=SOLVE_TIME_LIMIT_S).to_dict()
