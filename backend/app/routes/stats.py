import numpy as np
from fastapi import APIRouter
from app.database.db import get_conn, get_meta
from app.utils.format import loads

router = APIRouter(tags=["stats"])


def _sparkline(seed, trend=1.0, n=10):
    rng = np.random.RandomState(seed)
    vals = np.cumsum(rng.randn(n) * 3 + trend * 2)
    vals = vals - vals.min() + 5
    vals = 34 - (vals / vals.max()) * 30
    pts = " ".join(f"L{22*i+2} {v:.0f}" for i, v in enumerate(vals))
    return "M" + pts[1:]


@router.get("/stats")
async def get_stats():
    with get_conn() as conn:
        total_users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        flagged = conn.execute("SELECT COUNT(*) c FROM users WHERE level != 'safe'").fetchone()["c"]
        by_level = {r["level"]: r["c"] for r in conn.execute(
            "SELECT level, COUNT(*) c FROM users GROUP BY level").fetchall()}
        clusters = conn.execute(
            "SELECT * FROM clusters ORDER BY size DESC LIMIT 3").fetchall()
        biggest_cluster_size = conn.execute(
            "SELECT MAX(size) m FROM clusters").fetchone()["m"] or 0
        sage_row = conn.execute(
            "SELECT * FROM model_scores WHERE is_current = 1").fetchone()

        # tag frequency across flagged users -> "why accounts got flagged"
        rows = conn.execute("SELECT tags FROM users WHERE level != 'safe'").fetchall()

    tag_counts = {}
    for r in rows:
        for t in loads(r["tags"], []):
            tag_counts[t] = tag_counts.get(t, 0) + 1
    top_tags = sorted(tag_counts.items(), key=lambda kv: -kv[1])[:4]
    max_count = top_tags[0][1] if top_tags else 1
    palette = ["#34D399", "#8AB4F8", "#F8DCA8", "#F5C8D0"]
    flag_reasons = [
        {"label": label, "count": count, "width": f"{int(count/max_count*100)}%", "color": palette[i % 4]}
        for i, (label, count) in enumerate(top_tags)
    ]

    kpis = [
        {
            "label": "Accounts scanned", "badge": "90d", "value": f"{total_users:,}",
            "bg": "#B8E6D0", "ink": "#06251A", "labelInk": "#123528",
            "path": _sparkline(1, trend=1.0),
        },
        {
            "label": "Flagged fake", "badge": f"+{by_level.get('critical', 0)}", "value": f"{flagged:,}",
            "bg": "#F5C8D0", "ink": "#3D1620", "labelInk": "#3D1620",
            "path": _sparkline(2, trend=1.3),
        },
        {
            "label": "Bot clusters", "badge": str(len(clusters)), "value": str(biggest_cluster_size),
            "bg": "#C9D8F7", "ink": "#17244A", "labelInk": "#17244A",
            "note": "accounts in the largest ring",
        },
        {
            "label": "Precision @100", "badge": "labelled",
            "value": f"{sage_row['precision']:.2f}" if sage_row else "—",
            "bg": "#F8DCA8", "ink": "#42300C", "labelInk": "#42300C",
            "note": f"recall {sage_row['recall']:.2f} · AUC {sage_row['auc']:.2f}" if sage_row else "",
        },
    ]

    cluster_list = [
        {"tag": c["tag"], "name": c["name"], "detail": c["detail"], "size": c["size"]}
        for c in clusters
    ]

    return {"kpis": kpis, "flag_reasons": flag_reasons, "clusters": cluster_list}
