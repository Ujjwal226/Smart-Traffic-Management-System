"""
TrafficFlow AI – Live API Server
=================================
Serves:
  GET  /data        → latest simulation results JSON
  POST /update      → sim engine pushes live updates here
  GET  /stream      → Server-Sent Events stream of terminal log lines
  GET  /            → Health check
"""
import json
import time
import threading
from collections import deque

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="TrafficFlow AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory store ───────────────────────────────────────
_latest_data: dict = {}
_log_lines: deque = deque(maxlen=500)   # Keep last 500 log lines
_lock = threading.Lock()


@app.get("/")
def health():
    return {"status": "ok", "service": "TrafficFlow AI API"}


@app.post("/update")
async def update(payload: dict):
    """Called by sim_engine every 50 steps to push live results."""
    global _latest_data
    with _lock:
        _latest_data = payload
    return {"status": "received"}


@app.get("/data")
def get_data():
    """Dashboard polls this for live simulation data."""
    with _lock:
        if not _latest_data:
            return JSONResponse(content={}, status_code=204)
        return JSONResponse(content=_latest_data)


@app.post("/log")
async def post_log(payload: dict):
    """Receive a log line from the sim process."""
    line = payload.get("line", "")
    if line:
        with _lock:
            _log_lines.append({"ts": time.time(), "line": line})
    return {"status": "ok"}


@app.get("/stream")
def stream_logs():
    """Server-Sent Events: streams log lines to browser."""
    def event_generator():
        last_idx = 0
        while True:
            with _lock:
                lines = list(_log_lines)
            new_lines = lines[last_idx:]
            for entry in new_lines:
                yield f"data: {json.dumps(entry)}\n\n"
            last_idx = len(lines)
            time.sleep(0.3)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9000)
