from fastapi import APIRouter, Query
from typing import Optional
from app.database.db import get_conn
from app.utils.format import loads

router = APIRouter(tags=["graph"])


@router.get("/graph")
async def get_graph(
    cluster_id: Optional[str] = Query(None),
    risk_level: str = Query("all", pattern="^(all|critical|high|watch)$"),
    limit_nodes: int = Query(60, ge=10, le=300),
):
    with get_conn() as conn:
        if cluster_id:
            cluster = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
            member_ids = loads(cluster["members"], []) if cluster else []
        else:
            top_cluster = conn.execute("SELECT * FROM clusters ORDER BY size DESC LIMIT 1").fetchone()
            member_ids = loads(top_cluster["members"], []) if top_cluster else []
            cluster = top_cluster

        member_ids = member_ids[:limit_nodes]
        if not member_ids:
            return {"nodes": [], "edges": [], "clusters": []}

        placeholders = ",".join("?" for _ in member_ids)
        users = conn.execute(
            f"SELECT id, handle, score, level FROM users WHERE id IN ({placeholders})", member_ids
        ).fetchall()

        stars = conn.execute(
            f"SELECT user_id, repo_id FROM stars WHERE user_id IN ({placeholders}) LIMIT 400",
            member_ids,
        ).fetchall()
        repo_ids = list({s["repo_id"] for s in stars})
        repos = []
        if repo_ids:
            rp = ",".join("?" for _ in repo_ids)
            repos = conn.execute(f"SELECT id, name, score FROM repos WHERE id IN ({rp})", repo_ids).fetchall()

        follows = conn.execute(
            f"SELECT follower_id, following_id FROM follows "
            f"WHERE follower_id IN ({placeholders}) AND following_id IN ({placeholders})",
            member_ids + member_ids,
        ).fetchall()

        all_clusters = conn.execute("SELECT id, tag, name, size, risk_level FROM clusters").fetchall()

    nodes = [
        {"id": u["id"], "type": "user", "label": u["handle"], "score": int(u["score"]),
         "size": 12 + int(u["score"] / 6), "risk_level": u["level"]}
        for u in users
    ]
    nodes += [
        {"id": r["id"], "type": "repo", "label": r["name"], "score": int(r["score"]),
         "size": 16, "risk_level": "critical" if r["score"] >= 80 else "high" if r["score"] >= 60 else "watch"}
        for r in repos
    ]

    edges = [{"source": s["user_id"], "target": s["repo_id"], "type": "starred", "weight": 1} for s in stars]
    edges += [{"source": f["follower_id"], "target": f["following_id"], "type": "follows", "weight": 1}
              for f in follows]

    return {
        "nodes": nodes,
        "edges": edges,
        "clusters": [dict(c) for c in all_clusters],
        "focused_cluster": dict(cluster) if cluster else None,
    }
