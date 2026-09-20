import os
import csv
import uuid
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.config import settings
from app.database.db import get_conn

router = APIRouter(tags=["export"])


class ExportRequest(BaseModel):
    export_type: str = "users"  # users | repos
    risk_level: str = "all"
    min_score: int = 0


@router.post("/export")
async def export_data(req: ExportRequest):
    table = "users" if req.export_type == "users" else "repos"
    where = ["score >= ?"]
    params = [req.min_score]
    if req.risk_level != "all":
        where.append("level = ?" if table == "users" else "1=1")
        if table == "users":
            params.append(req.risk_level)

    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE {' AND '.join(where)} ORDER BY score DESC", params
        ).fetchall()
        cols = rows[0].keys() if rows else []

    filename = f"export_{uuid.uuid4().hex[:10]}.csv"
    path = os.path.join(settings.DATA_DIR, filename)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for r in rows:
            writer.writerow([r[c] for c in cols])

    return {
        "download_url": f"/api/export/download/{filename}",
        "filename": filename,
        "size_bytes": os.path.getsize(path),
    }


@router.get("/export/download/{filename}")
async def download_export(filename: str):
    path = os.path.join(settings.DATA_DIR, filename)
    return FileResponse(path, filename=filename, media_type="text/csv")
