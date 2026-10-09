import json
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from threading import Lock

from fastapi import FastAPI, Request, Query
from fastapi.responses import Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST


app = FastAPI(title="GA2 Observability Service")

START_TIME = time.monotonic()

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests received"
)

LOGS = deque(maxlen=1000)
LOG_LOCK = Lock()


def record_log(path: str, request_id: str):
    entry = {
        "level": "INFO",
        "ts": datetime.now(timezone.utc).isoformat(),
        "path": path,
        "request_id": request_id
    }

    with LOG_LOCK:
        LOGS.append(entry)


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())

    REQUEST_COUNT.inc()

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    record_log(request.url.path, request_id)

    return response


@app.get("/work")
async def work(n: int = Query(default=1, ge=0, le=100000)):
    # Perform a small amount of actual computation.
    result = sum(range(n + 1))

    return {
        "email": "ga2-observability@example.com",
        "done": n
    }


@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/healthz")
async def healthz():
    uptime = max(0.0, time.monotonic() - START_TIME)

    return {
        "status": "ok",
        "uptime_s": uptime
    }


@app.get("/logs/tail")
async def logs_tail(
    limit: int = Query(default=10, ge=0, le=1000)
):
    with LOG_LOCK:
        entries = list(LOGS)

    return entries[-limit:] if limit else []