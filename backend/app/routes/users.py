from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.database.db import get_conn
from app.utils.format import row_to_user_card, loads

router = APIRouter(tags=["users"])

SORT_COLUMNS = {"score": "score", "age": "created_at", "links": "links"}


@router.get("/users")
async def get_users(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort: str = Query("score", pattern="^(score|age|links)$"),
    level: Optional[str] = Query(None, pattern="^(critical|high|watch|safe|all|any)$"),
    search: Optional[str] = Query(None, max_length=100),
):
    col = SORT_COLUMNS[sort]
    direction = "DESC" if sort != "age" else "ASC"

    where = []
    params = []
    if level == "any":
        pass  # explicitly requested: include safe/clean accounts too
    elif level and level != "all":
        where.append("level = ?")
        params.append(level)
    else:
        # This is a fraud dashboard — "all" (the default) means "all
        # flagged accounts", not the entire scanned population. Genuine
        # clean accounts are reachable with level=any if ever needed.
        where.append("level != 'safe'")
    if search:
        where.append("handle LIKE ?")
        params.append(f"%{search}%")
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    with get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) c FROM users {where_sql}", params).fetchone()["c"]
        rows = conn.execute(
            f"SELECT * FROM users {where_sql} ORDER BY {col} {direction} LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()

        # counts per level for filter chips
        level_counts = {r["level"]: r["c"] for r in conn.execute(
            "SELECT level, COUNT(*) c FROM users GROUP BY level"
        ).fetchall()}

    return {
        "users": [row_to_user_card(r) for r in rows],
        "total": total,
        "has_more": offset + limit < total,
        "level_counts": level_counts,
    }


@router.get("/users/{user_id}")
async def get_user_detail(user_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        starred = conn.execute(
            "SELECT s.repo_id, s.starred_at, r.name FROM stars s JOIN repos r ON r.id = s.repo_id "
            "WHERE s.user_id = ? ORDER BY s.starred_at DESC LIMIT 50",
            (user_id,),
        ).fetchall()

        peer_handles = loads(row["peers"], [])
        peer_rows = []
        if peer_handles:
            placeholders = ",".join("?" for _ in peer_handles if not _.startswith("+"))
            clean_handles = [h for h in peer_handles if not h.startswith("+")]
            if clean_handles:
                peer_rows = conn.execute(
                    f"SELECT id, handle, score, level FROM users WHERE handle IN ({placeholders})",
                    clean_handles,
                ).fetchall()

    card = row_to_user_card(row)
    card.update({
        "github_url": f"https://github.com/{row['handle'].lstrip('@')}",
        "created_at": row["created_at"],
        "followers": row["followers"],
        "following": row["following"],
        "public_repos": row["public_repos"],
        "public_gists": row["public_gists"],
        "starred_repos": [
            {"name": s["name"], "repo_id": s["repo_id"], "starred_at": s["starred_at"]} for s in starred
        ],
        "peers_detail": [dict(p) for p in peer_rows],
    })
    return card
