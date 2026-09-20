"""Live GitHub scan — inference only.

This deliberately mirrors routes/analysis.py's job pattern, but it is NOT
the same kind of operation and the API says so:

    /analysis/run   regenerates the synthetic graph and TRAINS the GNN.
                    Ground truth is known, so it reports precision/recall.

    /real-scan/run  points the ALREADY-trained weights at live GitHub and
                    runs a forward pass. Real accounts carry no fraud
                    labels, so there is nothing to train against and no
                    accuracy number that would mean anything.

Anything returned here is a transfer check, not an evaluation.
"""
import json
import os
import threading
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings

router = APIRouter(tags=["real-scan"])

_RUNS = {}
_LOCK = threading.Lock()

# Survives a reload so the tab isn't blank after the server restarts.
# Git-ignored: these are real GitHub handles.
LATEST_PATH = os.path.join(settings.DATA_DIR, "real_scan_latest.json")

TOKEN_HELP = (
    "GITHUB_TOKEN is not set on the backend. Profile lookups use the GraphQL "
    "API, which requires authentication — without it every account scores 0 "
    "and the scan would look clean because it measured nothing. Create a "
    "classic token (no scopes needed) at https://github.com/settings/tokens, "
    "then either set GITHUB_TOKEN in your environment or put it in "
    "backend/.env, and restart the backend."
)


def _resolve_token():
    """real_data.py reads os.environ directly; Settings reads backend/.env.
    Bridge the two so either source works."""
    token = os.environ.get("GITHUB_TOKEN") or settings.GITHUB_TOKEN or ""
    if token and not os.environ.get("GITHUB_TOKEN"):
        os.environ["GITHUB_TOKEN"] = token
    return token


class RealScanRequest(BaseModel):
    repos: list[str] | None = None
    max_profiles: int = 150


def _run_in_background(scan_id: str, repos, max_profiles: int):
    from app.services.real_data import run_real_test

    with _LOCK:
        _RUNS[scan_id]["status"] = "running"
    try:
        payload = run_real_test(repos=repos, max_profile_lookups=max_profiles)
        payload["scanned_at"] = datetime.utcnow().isoformat()
        payload["max_profiles"] = max_profiles
        with _LOCK:
            _RUNS[scan_id]["status"] = "completed"
            _RUNS[scan_id]["result"] = payload
        try:
            with open(LATEST_PATH, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
        except OSError as exc:
            print("real-scan: could not cache results — %s" % exc)
    except Exception as exc:
        with _LOCK:
            _RUNS[scan_id]["status"] = "failed"
            _RUNS[scan_id]["error"] = str(exc)


@router.post("/real-scan/run")
async def run_real_scan(req: RealScanRequest):
    # Fail before spawning the thread so the UI gets the reason immediately
    # rather than a job that dies three seconds later.
    if not _resolve_token():
        raise HTTPException(status_code=400, detail=TOKEN_HELP)

    scan_id = "scan_%s" % uuid.uuid4().hex[:12]
    _RUNS[scan_id] = {
        "scan_id": scan_id,
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
    }
    threading.Thread(
        target=_run_in_background,
        args=(scan_id, req.repos, req.max_profiles),
        daemon=True,
    ).start()
    return {
        "scan_id": scan_id,
        "status": "running",
        "started_at": _RUNS[scan_id]["started_at"],
        "trains_model": False,
    }


@router.get("/real-scan/status/{scan_id}")
async def real_scan_status(scan_id: str):
    if scan_id not in _RUNS:
        raise HTTPException(status_code=404, detail="Scan not found")
    return _RUNS[scan_id]


@router.get("/real-scan/latest")
async def real_scan_latest():
    """Last completed scan, in memory or from the cache on disk."""
    with _LOCK:
        done = [r for r in _RUNS.values() if r.get("status") == "completed"]
    if done:
        return done[-1]["result"]
    if os.path.exists(LATEST_PATH):
        try:
            with open(LATEST_PATH, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            pass
    return {"results": [], "never_run": True, "token_configured": bool(_resolve_token())}


@router.get("/real-scan/config")
async def real_scan_config():
    return {"token_configured": bool(_resolve_token()), "token_help": TOKEN_HELP}
