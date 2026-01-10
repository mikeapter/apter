from __future__ import annotations

import threading
import time
import uuid
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    import psutil  # optional, but you installed it
except Exception:
    psutil = None


# -----------------------------
# Models
# -----------------------------
class HealthOut(BaseModel):
    ok: bool = True
    service: str = "control-plane"
    time: float
    cpu_percent: Optional[float] = None
    mem_percent: Optional[float] = None


class ProfileOut(BaseModel):
    id: str
    name: str


class RunOut(BaseModel):
    run_id: str
    profile_id: str
    status: str
    started_at: float
    stopped_at: Optional[float] = None


class StartBotRequest(BaseModel):
    profile_id: str = Field(default="paper", description="Which profile to run (paper/live/etc.)")


class StopBotRequest(BaseModel):
    run_id: Optional[str] = Field(default=None, description="Stop a specific run_id (or latest active if omitted)")


class LogsOut(BaseModel):
    run_id: str
    lines: List[str]


# -----------------------------
# In-memory state (simple starter)
# -----------------------------
PROFILES: Dict[str, ProfileOut] = {
    "paper": ProfileOut(id="paper", name="Paper Trading"),
    "pilot": ProfileOut(id="pilot", name="Pilot / Small Size"),
    "live": ProfileOut(id="live", name="Live (Restricted)"),
}

RUNS: Dict[str, RunOut] = {}
LOGS: Dict[str, List[str]] = {}
RUN_THREADS: Dict[str, threading.Thread] = {}
RUN_STOP_EVENTS: Dict[str, threading.Event] = {}


def _log(run_id: str, msg: str) -> None:
    LOGS.setdefault(run_id, [])
    stamp = time.strftime("%H:%M:%S")
    LOGS[run_id].append(f"[{stamp}] {msg}")


def _runner(run_id: str, profile_id: str, stop_event: threading.Event) -> None:
    _log(run_id, f"Run started (profile={profile_id}).")
    i = 0
    try:
        while not stop_event.is_set():
            i += 1
            _log(run_id, f"Heartbeat {i} (bot loop placeholder).")
            time.sleep(1.0)

            # For a demo starter, auto-stop after a bit so it doesn't run forever
            if i >= 30:
                _log(run_id, "Auto-stop reached (demo limit).")
                break

        _log(run_id, "Run stopping...")
    except Exception as e:
        _log(run_id, f"Run crashed: {type(e).__name__}: {e}")
    finally:
        run = RUNS.get(run_id)
        if run:
            run.status = "stopped"
            run.stopped_at = time.time()
        _log(run_id, "Run ended.")


# -----------------------------
# App
# -----------------------------
app = FastAPI(title="BotTrader Control Plane", version="0.1.0")

# Allow your Next.js dev server to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    cpu = None
    mem = None
    if psutil is not None:
        try:
            cpu = float(psutil.cpu_percent(interval=0.05))
            mem = float(psutil.virtual_memory().percent)
        except Exception:
            cpu = None
            mem = None

    return HealthOut(time=time.time(), cpu_percent=cpu, mem_percent=mem)


@app.get("/v1/profiles", response_model=List[ProfileOut])
def list_profiles() -> List[ProfileOut]:
    return list(PROFILES.values())


@app.get("/v1/runs", response_model=List[RunOut])
def list_runs() -> List[RunOut]:
    # newest first
    return sorted(RUNS.values(), key=lambda r: r.started_at, reverse=True)


@app.post("/v1/bot/start", response_model=RunOut)
def start_bot(req: StartBotRequest) -> RunOut:
    profile_id = req.profile_id.strip()
    if profile_id not in PROFILES:
        raise HTTPException(status_code=400, detail=f"Unknown profile_id: {profile_id}")

    run_id = uuid.uuid4().hex[:12]
    run = RunOut(run_id=run_id, profile_id=profile_id, status="running", started_at=time.time())
    RUNS[run_id] = run
    LOGS[run_id] = []

    stop_event = threading.Event()
    RUN_STOP_EVENTS[run_id] = stop_event

    t = threading.Thread(target=_runner, args=(run_id, profile_id, stop_event), daemon=True)
    RUN_THREADS[run_id] = t
    t.start()

    _log(run_id, "Control plane start_bot completed.")
    return run


@app.post("/v1/bot/stop", response_model=RunOut)
def stop_bot(req: StopBotRequest) -> RunOut:
    run_id = req.run_id

    if not run_id:
        # stop latest active run
        active = [r for r in RUNS.values() if r.status == "running"]
        if not active:
            raise HTTPException(status_code=404, detail="No active runs to stop.")
        active.sort(key=lambda r: r.started_at, reverse=True)
        run_id = active[0].run_id

    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Unknown run_id: {run_id}")

    if run.status != "running":
        return run

    stop_event = RUN_STOP_EVENTS.get(run_id)
    if stop_event is None:
        run.status = "stopped"
        run.stopped_at = time.time()
        return run

    _log(run_id, "Stop requested.")
    stop_event.set()
    return run


@app.get("/v1/runs/{run_id}/logs", response_model=LogsOut)
def get_logs(run_id: str) -> LogsOut:
    if run_id not in RUNS:
        # ✅ THIS is where your file had the broken f-string/brace before
        raise HTTPException(status_code=404, detail=f"Unknown run_id: {run_id}")

    lines = LOGS.get(run_id, [])
    return LogsOut(run_id=run_id, lines=lines)
