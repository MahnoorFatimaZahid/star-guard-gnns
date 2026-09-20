from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.database.db import get_conn
from app.utils.format import row_to_repo_card

router = APIRouter(tags=["repos"])

SORT_COLUMNS = {"score": "score", "stars": "stars", "flagged_count": "flagged_count"}


@router.get("/repos")
async def get_repos(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort: str = Query("score", pattern="^(score|stars|flagged_count)$"),
    search: Optional[str] = Query(None, max_length=100),
):
    where_sql = ""
    params = []
    if search:
        where_sql = "WHERE name LIKE ?"
        params.append(f"%{search}%")

    col = SORT_COLUMNS[sort]
    with get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) c FROM repos {where_sql}", params).fetchone()["c"]
        rows = conn.execute(
            f"SELECT * FROM repos {where_sql} ORDER BY {col} DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()

    return {
        "repos": [row_to_repo_card(r) for r in rows],
        "total": total,
        "has_more": offset + limit < total,
    }


@router.get("/repos/{owner}/{repo}")
async def get_repo_detail(owner: str, repo: str):
    full_name = f"{owner}/{repo}"
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM repos WHERE name = ?", (full_name,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Repo not found")

        stargazers = conn.execute(
            "SELECT s.user_id, s.starred_at, u.handle, u.score, u.level "
            "FROM stars s JOIN users u ON u.id = s.user_id "
            "WHERE s.repo_id = ? AND u.level != 'safe' "
            "ORDER BY u.score DESC LIMIT 100",
            (row["id"],),
        ).fetchall()

    card = row_to_repo_card(row)
    card.update({
        "created_at": row["created_at"],
        "pushed_at": row["pushed_at"],
        "language": row["language"],
        "description": row["description"],
        "suspicious_stargazers": [dict(s) for s in stargazers],
    })
    return card
