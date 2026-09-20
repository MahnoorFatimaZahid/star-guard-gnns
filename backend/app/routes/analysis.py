import threading
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database.db import get_meta, set_meta

router = APIRouter(tags=["analysis"])

_RUNS = {}  # in-memory status tracker (single-process demo backend)
_LOCK = threading.Lock()


class AnalysisRequest(BaseModel):
    data_source: str = "github"
    lookback_days: int = 90
    min_repos: int = 10


def _run_in_background(analysis_id: str):
    from app.services.pipeline import run_pipeline
    with _LOCK:
        _RUNS[analysis_id]["status"] = "running"
        _RUNS[analysis_id]["progress"] = 5
    try:
        # run_pipeline regenerates data + retrains the GNN end-to-end
        run_pipeline()
        with _LOCK:
            _RUNS[analysis_id]["status"] = "completed"
            _RUNS[analysis_id]["progress"] = 100
    except Exception as e:
        with _LOCK:
            _RUNS[analysis_id]["status"] = "failed"
            _RUNS[analysis_id]["error"] = str(e)


@router.post("/analysis/run")
async def run_analysis(req: AnalysisRequest):
    analysis_id = f"ana_{uuid.uuid4().hex[:12]}"
    _RUNS[analysis_id] = {
        "analysis_id": analysis_id,
        "status": "running",
        "progress": 0,
        "started_at": datetime.utcnow().isoformat(),
    }
    thread = threading.Thread(target=_run_in_background, args=(analysis_id,), daemon=True)
    thread.start()
    return {
        "analysis_id": analysis_id,
        "status": "running",
        "started_at": _RUNS[analysis_id]["started_at"],
        "estimated_duration_seconds": 60,
    }


@router.get("/analysis/{analysis_id}/status")
async def get_analysis_status(analysis_id: str):
    if analysis_id not in _RUNS:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _RUNS[analysis_id]


@router.get("/analysis/last")
async def last_run_meta():
    return get_meta("last_run", default={})
