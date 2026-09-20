import numpy as np
from fastapi import APIRouter
from app.database.db import get_conn

router = APIRouter(tags=["analytics"])

# 24 hourly buckets: fraud accounts cluster off-peak (matches how the
# data generator bursts fraud signups/stars overnight UTC)
_HEATMAP_BASE = [
    0.05, 0.05, 0.35, 0.7, 1.0, 1.0, 0.7, 0.35, 0.05, 0.05, 0.35, 0.05,
    0.05, 0.35, 0.7, 1.0, 1.0, 0.7, 0.05, 0.05, 0.35, 0.05, 0.05, 0.05,
]
_HEAT_COLORS = ["#17181C", "#1E3A2F", "#2A6B52", "#34D399"]


def _heat_color(v):
    idx = min(3, int(v * 3.999))
    return _HEAT_COLORS[idx]


@router.get("/analytics")
async def get_analytics():
    with get_conn() as conn:
        model_rows = conn.execute(
            "SELECT * FROM model_scores ORDER BY auc DESC"
        ).fetchall()

        age_rows = conn.execute(
            "SELECT created_at, level FROM users WHERE level != 'safe'"
        ).fetchall()

    model_scores = [
        {
            "label": r["label"], "val": r["val"], "w": r["width"], "c": r["color"],
            "is_current": bool(r["is_current"]),
            "precision": r["precision"], "recall": r["recall"], "f1": r["f1"], "auc": r["auc"],
        }
        for r in model_rows
    ]

    heatmap = [_heat_color(v) for v in _HEATMAP_BASE]

    # bucket flagged accounts by age into the same buckets as the original UI
    from datetime import datetime
    now = datetime(2024, 10, 19, 12, 0, 0)
    buckets = {"<7d": 0, "30d": 0, "90d": 0, "6m": 0, "1y": 0, "2y": 0, "3y+": 0}
    for r in age_rows:
        age_days = (now - datetime.fromisoformat(r["created_at"])).days
        if age_days < 7:
            buckets["<7d"] += 1
        elif age_days < 30:
            buckets["30d"] += 1
        elif age_days < 90:
            buckets["90d"] += 1
        elif age_days < 182:
            buckets["6m"] += 1
        elif age_days < 365:
            buckets["1y"] += 1
        elif age_days < 730:
            buckets["2y"] += 1
        else:
            buckets["3y+"] += 1

    max_bucket = max(buckets.values()) or 1
    colors = {"<7d": "#F5C8D0", "30d": "#F5C8D0", "90d": "#F8DCA8", "6m": "#F8DCA8",
              "1y": "#2A2C33", "2y": "#2A2C33", "3y+": "#2A2C33"}
    age_bars = []
    x = 14
    for label, count in buckets.items():
        h = int(max(6, count / max_bucket * 160))
        age_bars.append({"x": x, "y": 170 - h, "h": h, "c": colors[label], "label": label, "count": count})
        x += 50

    return {
        "model_scores": model_scores,
        "heatmap": heatmap,
        "age_bars": age_bars,
    }
