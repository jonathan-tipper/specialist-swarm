"""Local web UI for the Incident War-Room.

One button, one incident, one live log — wraps swarm.runner.run_session in a
Server-Sent Events endpoint so the browser watches the same fan-out
run_war_room.py prints to the terminal.

Usage:
    python webapp.py
"""

import json
import os
import threading

import uvicorn
from anthropic import Anthropic
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from run_war_room import OUTPUT_DIR, TITLE, kickoff_message
from swarm.runner import run_session
from swarm.store import IdStore

OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI()
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

_run_lock = threading.Lock()


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@app.get("/")
def index() -> FileResponse:
    return FileResponse("web/index.html")


@app.get("/events")
def events() -> StreamingResponse:
    def stream():
        if not _run_lock.acquire(blocking=False):
            yield _sse({"kind": "error", "message": "A run is already in progress."})
            return
        try:
            store = IdStore()
            commander_id = store.get("coordinator")
            environment_id = store.get("environment")
            if not commander_id or not environment_id:
                yield _sse({
                    "kind": "error",
                    "message": (
                        "Missing commander or environment. Run, in order: "
                        "python setup_environment.py, python create_specialists.py, "
                        "python upload_skills.py, python create_coordinator.py"
                    ),
                })
                return

            client = Anthropic()
            text = kickoff_message()
            for event in run_session(
                client,
                commander_id,
                environment_id,
                text,
                TITLE,
                workspace=os.environ.get("ANTHROPIC_WORKSPACE_ID"),
                output_dir=OUTPUT_DIR,
            ):
                yield _sse(event)
        finally:
            _run_lock.release()

    return StreamingResponse(stream(), media_type="text/event-stream")


if __name__ == "__main__":
    print("War-room UI: http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
